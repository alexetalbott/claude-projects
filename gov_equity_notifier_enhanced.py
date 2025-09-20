#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced EDGAR scan + email notifier for U.S. Government equity stakes in 8-Ks.
Improved false positive filtering and confidence scoring.

Exit codes:
  0 = ran fine (new hits may or may not exist)
  1 = configuration error
  2 = network/SEC error
  3 = email failure
"""

import os, re, sqlite3, sys, smtplib, textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# -------------------
# Enhanced filtering patterns
# -------------------

# Government entities - more specific patterns
GOVERNMENT_ENTITIES = [
    r"\bU\.S\. Government\b",
    r"\bUnited States Government\b",
    r"\bDepartment of Commerce\b",
    r"\bDepartment of Defense\b",
    r"\bDOD\b",
    r"\bDOC\b",
    r"\bTreasury Department\b",
    r"\bU\.S\. Treasury\b",
    r"\bNational Security\b",
    r"\bCHIPS and Science Act\b",
    r"\bCHIPS Act\b",
    r"\bDefense Production Act\b",
    r"\bCommittee on Foreign Investment\b",
    r"\bCFIUS\b"
]

# Investment/transaction terms - more precise
INVESTMENT_TERMS = [
    r"\bequity investment\b",
    r"\bequity stake\b",
    r"\bequity position\b",
    r"\bpreferred shares\b",
    r"\bpreferred stock investment\b",
    r"\bstock purchase\b",
    r"\bwarrant agreement\b",
    r"\bwarrant issuance\b",
    r"\bconvertible preferred\b",
    r"\bseries [A-Z] preferred\b",
    r"\binvestment agreement\b",
    r"\bpurchase agreement\b",
    r"\bfunding agreement\b",
    r"\bcapital investment\b"
]

# Transaction indicators - signals of actual deals
TRANSACTION_INDICATORS = [
    r"\$[\d,]+\s*(million|billion)\s*(investment|funding|purchase)",
    r"(received|obtained|secured)\s+\$[\d,]+",
    r"(closing|completion)\s+of.*investment",
    r"(entered into|executed|signed).*agreement",
    r"(purchase|issuance)\s+of.*shares",
    r"(funding|investment).*of\s+\$[\d,]+",
    r"(total|aggregate)\s+(funding|investment)",
    r"(first|initial|additional)\s+tranche"
]

# Common false positive contexts to exclude
FALSE_POSITIVE_EXCLUSIONS = [
    r"risk.*factors?",
    r"material.*weakness",
    r"legal.*proceedings?",
    r"forward.*looking.*statements?",
    r"hypothetical",
    r"example",
    r"illustration",
    r"may.*be.*subject.*to",
    r"could.*be.*impacted.*by",
    r"potential.*future",
    r"general.*economic.*conditions",
    r"regulatory.*environment",
    r"bond.*market",
    r"debt.*securities",
    r"credit.*facility"
]

SNIPPET_CHARS = 120  # Tighter context window
PROXIMITY_CHARS = 150  # Stricter proximity requirement

DB_PATH = os.path.join(os.path.dirname(__file__), "gov_equity_seen.sqlite3")

# ---------------
# Enhanced analysis functions
# ---------------

def must_get_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[config] Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
          cik TEXT NOT NULL,
          accession TEXT NOT NULL,
          confidence REAL DEFAULT 0.0,
          PRIMARY KEY (cik, accession)
        )
    """)
    conn.commit()
    return conn

def seen_before(conn, cik, accession) -> bool:
    cur = conn.execute("SELECT 1 FROM seen WHERE cik=? AND accession=?", (cik, accession))
    return cur.fetchone() is not None

def mark_seen(conn, cik, accession, confidence=0.0):
    conn.execute("INSERT OR IGNORE INTO seen (cik, accession, confidence) VALUES (?, ?, ?)",
                (cik, accession, confidence))
    conn.commit()

def get_json(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def get_text(url, headers):
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.text

def latest_master_idx_url(headers):
    """Get the most recent master index file from SEC EDGAR."""
    from datetime import datetime, timedelta

    # Try recent business days
    for days_back in range(1, 10):
        test_date = datetime.now() - timedelta(days=days_back)

        # Skip weekends
        if test_date.weekday() >= 5:
            continue

        year = test_date.year
        quarter = (test_date.month - 1) // 3 + 1
        date_str = test_date.strftime("%y%m%d")

        test_url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/master.{date_str}.idx"

        try:
            # Test if file exists
            response = requests.head(test_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return test_url
        except:
            continue

    raise RuntimeError("No accessible master index found in past 10 days")

def parse_master_idx(text):
    """Yields dicts with company, cik, form, date, path, accession."""
    for line in text.splitlines():
        if "|8-K|" in line:
            parts = line.split("|")
            if len(parts) >= 5:
                cik, company, form, date, path = parts[0:5]
                try:
                    accession = path.strip().split("/")[3]
                except Exception:
                    accession = ""
                yield {
                    "company": company.strip(),
                    "cik": cik.strip(),
                    "form": form.strip(),
                    "date": date.strip(),
                    "path": path.strip(),
                    "accession": accession,
                }

def calculate_confidence_score(html_text: str, matches: List[Tuple]) -> float:
    """Calculate confidence score based on various signals."""
    score = 0.0
    text_lower = html_text.lower()

    # Base score for any match
    score += 0.3

    # Bonus for multiple government entity mentions
    gov_mentions = sum(1 for pattern in GOVERNMENT_ENTITIES
                      if re.search(pattern, html_text, re.I))
    score += min(gov_mentions * 0.1, 0.3)

    # High bonus for transaction indicators with dollar amounts
    transaction_matches = sum(1 for pattern in TRANSACTION_INDICATORS
                            if re.search(pattern, html_text, re.I))
    score += transaction_matches * 0.4

    # Bonus for specific 8-K items that typically contain material agreements
    if re.search(r"item\s+(1\.01|3\.02)", text_lower):
        score += 0.2

    # Penalty for false positive contexts
    fp_matches = sum(1 for pattern in FALSE_POSITIVE_EXCLUSIONS
                    if re.search(pattern, html_text, re.I))
    score -= fp_matches * 0.15

    # Bonus for being in first half of document (material info usually comes first)
    if len(matches) > 0:
        avg_position = sum(html_text.find(match[1]) for match in matches) / len(matches)
        if avg_position < len(html_text) * 0.5:
            score += 0.1

    return max(0.0, min(1.0, score))

def scan_filing_for_hits(url, headers) -> Tuple[List[Tuple], float]:
    """Enhanced scanning with confidence scoring."""
    html = get_text(url, headers)

    # Clean up HTML for better text analysis
    soup = BeautifulSoup(html, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    clean_text = soup.get_text()

    # Find government entity mentions
    gov_matches = []
    for pattern in GOVERNMENT_ENTITIES:
        for match in re.finditer(pattern, clean_text, flags=re.IGNORECASE):
            gov_matches.append((pattern, match))

    if not gov_matches:
        return [], 0.0

    # Find investment term mentions
    investment_matches = []
    for pattern in INVESTMENT_TERMS:
        for match in re.finditer(pattern, clean_text, flags=re.IGNORECASE):
            investment_matches.append((pattern, match))

    if not investment_matches:
        return [], 0.0

    # Check proximity between government and investment terms
    valid_matches = []
    for gov_pattern, gov_match in gov_matches:
        for inv_pattern, inv_match in investment_matches:
            distance = abs(gov_match.start() - inv_match.start())
            if distance <= PROXIMITY_CHARS:
                # Create context snippet
                start = max(0, min(gov_match.start(), inv_match.start()) - SNIPPET_CHARS)
                end = min(len(clean_text), max(gov_match.end(), inv_match.end()) + SNIPPET_CHARS)
                snippet = re.sub(r'\s+', ' ', clean_text[start:end]).strip()

                valid_matches.append((f"{gov_pattern} + {inv_pattern}", snippet))
                break  # Avoid duplicate matches for same gov entity

    if not valid_matches:
        return [], 0.0

    # Check for false positive exclusions
    for exclusion_pattern in FALSE_POSITIVE_EXCLUSIONS:
        if re.search(exclusion_pattern, clean_text, re.I):
            # If found in proximity to our matches, reduce confidence
            for _, snippet in valid_matches:
                if re.search(exclusion_pattern, snippet, re.I):
                    return [], 0.0  # Strong false positive signal

    confidence = calculate_confidence_score(clean_text, valid_matches)

    # Only return matches above minimum confidence threshold
    if confidence < 0.4:
        return [], confidence

    return valid_matches, confidence

def build_email(subject, html_body, text_body, sender, recipient):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg

def send_email(msg, host, port, user, password):
    with smtplib.SMTP(host, int(port)) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)

def main():
    load_dotenv()

    ua = must_get_env("SEC_USER_AGENT")
    smtp_host = must_get_env("SMTP_HOST")
    smtp_port = must_get_env("SMTP_PORT")
    smtp_user = must_get_env("SMTP_USER")
    smtp_pass = must_get_env("SMTP_PASS")
    from_email = must_get_env("FROM_EMAIL")
    to_email = must_get_env("TO_EMAIL")

    headers = {"User-Agent": ua}
    conn = init_db()

    try:
        idx_url = latest_master_idx_url(headers)
        idx_text = get_text(idx_url, headers)
    except Exception as e:
        print(f"[error] Failed to retrieve master idx: {e}", file=sys.stderr)
        sys.exit(2)

    base = "https://www.sec.gov/Archives/"
    new_hits = []

    for rec in parse_master_idx(idx_text):
        if not rec["accession"]:
            continue
        if seen_before(conn, rec["cik"], rec["accession"]):
            continue

        filing_index_url = urljoin(base, rec["path"])
        try:
            file_html = get_text(filing_index_url, headers)
            soup = BeautifulSoup(file_html, "html.parser")

            # Try to get the main 8-K document
            doc_link = soup.find("a", href=True, string=re.compile(r"\.htm(l)?$", re.I))
            doc_url = filing_index_url if not doc_link else urljoin(
                filing_index_url.rsplit("/", 1)[0] + "/", doc_link["href"]
            )

            hits, confidence = scan_filing_for_hits(doc_url, headers)

            if hits and confidence >= 0.4:  # Only include high-confidence matches
                new_hits.append((rec, doc_url, hits, confidence))
                mark_seen(conn, rec["cik"], rec["accession"], confidence)

        except Exception as e:
            print(f"[warn] Error scanning {filing_index_url}: {e}", file=sys.stderr)
            continue

    if not new_hits:
        print("[info] No new high-confidence govt-equity hits today.")
        sys.exit(0)

    # Sort by confidence score (highest first)
    new_hits.sort(key=lambda x: x[3], reverse=True)

    # Build email with confidence indicators
    today = datetime.utcnow().strftime("%Y-%m-%d")
    high_conf = [h for h in new_hits if h[3] >= 0.7]
    subject = f"[EDGAR] {len(high_conf)} high-conf + {len(new_hits)-len(high_conf)} med-conf govt equity alerts · {today}"

    # Text part with confidence scores
    lines = [f"Found {len(new_hits)} potential hits (sorted by confidence):\n"]
    for (rec, url, hits, conf) in new_hits:
        conf_label = "HIGH" if conf >= 0.7 else "MEDIUM"
        lines.append(f"• [{conf_label} {conf:.2f}] {rec['company']} ({rec['cik']}) · {rec['form']} · {rec['date']}")
        lines.append(f"  {url}")
        for i, (pattern, snippet) in enumerate(hits[:2], 1):
            lines.append(f"  → {textwrap.shorten(snippet, width=280, placeholder='…')}")
        lines.append("")
    text_body = "\n".join(lines)

    # HTML part with confidence styling
    html_rows = []
    for (rec, url, hits, conf) in new_hits:
        conf_label = "HIGH" if conf >= 0.7 else "MED"
        conf_color = "#28a745" if conf >= 0.7 else "#ffc107"

        snippets_html = "".join(
            f"<li style='margin:4px 0;'><code style='background:#f8f9fa;padding:2px 4px;'>{textwrap.shorten(snippet, width=300, placeholder='…')}</code></li>"
            for pattern, snippet in hits[:2]
        )

        html_rows.append(f"""
          <tr>
            <td style="padding:12px;border-bottom:1px solid #dee2e6;vertical-align:top;">
              <div style="display:flex;align-items:center;margin-bottom:8px;">
                <span style="background:{conf_color};color:white;padding:2px 6px;border-radius:3px;font-size:11px;font-weight:bold;margin-right:8px;">{conf_label} {conf:.2f}</span>
                <strong>{rec['company']} ({rec['cik']})</strong>
              </div>
              <div style="color:#6c757d;margin-bottom:8px;">{rec['form']} · {rec['date']}</div>
              <div style="margin-bottom:8px;"><a href="{url}" style="color:#007bff;">{url}</a></div>
              <ul style="margin:0;padding-left:20px;color:#495057;">{snippets_html}</ul>
            </td>
          </tr>
        """)

    html_body = f"""
    <html><body style="font-family:system-ui,-apple-system,sans-serif;">
      <p>Found <b>{len(new_hits)}</b> potential U.S. government equity disclosures (ranked by confidence):</p>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;border:1px solid #dee2e6;">
        {''.join(html_rows)}
      </table>
      <p style="color:#6c757d;font-size:12px;margin-top:16px;">
        Enhanced filtering with confidence scoring. HIGH ≥ 0.7, MEDIUM ≥ 0.4. Verify details in actual 8-K filing.
      </p>
    </body></html>
    """

    try:
        msg = build_email(subject, html_body, text_body, from_email, to_email)
        send_email(msg, smtp_host, smtp_port, smtp_user, smtp_pass)
        print(f"[info] Emailed {len(new_hits)} hit(s) ({len(high_conf)} high-confidence) to {to_email}")
        sys.exit(0)
    except Exception as e:
        print(f"[error] Email send failed: {e}", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()