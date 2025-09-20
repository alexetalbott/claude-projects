#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test version of the government equity notifier - no email sending.
"""

import os, re, sqlite3, sys
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Same patterns as main script
GOVERNMENT_ENTITIES = [
    r"\bU\.S\. Government\b",
    r"\bUnited States Government\b",
    r"\bDepartment of Commerce\b",
    r"\bDepartment of Defense\b",
    r"\bDOD\b",
    r"\bDOC\b",
    r"\bCHIPS and Science Act\b",
    r"\bCHIPS Act\b",
]

INVESTMENT_TERMS = [
    r"\bequity investment\b",
    r"\bequity stake\b",
    r"\bpreferred stock investment\b",
    r"\bstock purchase\b",
    r"\bwarrant agreement\b",
    r"\binvestment agreement\b",
]

PROXIMITY_CHARS = 150
SNIPPET_CHARS = 120

def get_json(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def get_text(url, headers):
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.text

def latest_master_idx_url(headers):
    # Try a recent business day that should have data
    from datetime import datetime, timedelta

    # Try yesterday first, then previous business days
    for days_back in range(1, 8):
        test_date = datetime.now() - timedelta(days=days_back)
        year = test_date.year
        quarter = (test_date.month - 1) // 3 + 1

        base_url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/"
        date_str = test_date.strftime("%y%m%d")
        test_url = f"{base_url}master.{date_str}.idx"

        print(f"   Trying: {test_url}")
        try:
            response = requests.head(test_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return test_url
        except:
            continue

    raise RuntimeError("No accessible master index found in past week")

def parse_master_idx(text):
    count = 0
    for line in text.splitlines():
        if "|8-K|" in line:
            count += 1
            if count <= 10:  # Only test first 10 8-Ks
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

def test_scan_filing(url, headers):
    """Simplified scanning for testing."""
    try:
        html = get_text(url, headers)
        soup = BeautifulSoup(html, 'html.parser')
        clean_text = soup.get_text()

        # Look for any government mentions
        gov_found = False
        for pattern in GOVERNMENT_ENTITIES:
            if re.search(pattern, clean_text, re.I):
                gov_found = True
                break

        if gov_found:
            return True, "Found government mention"
        return False, "No government mentions"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    load_dotenv()

    ua = os.getenv("SEC_USER_AGENT", "Test User (test@example.com)")
    headers = {"User-Agent": ua}

    print("🔍 Testing EDGAR access and parsing...")

    try:
        print("📡 Fetching latest master index...")
        idx_url = latest_master_idx_url(headers)
        print(f"   Using: {idx_url}")

        idx_text = get_text(idx_url, headers)
        print(f"   Retrieved {len(idx_text)} characters")

        base = "https://www.sec.gov/Archives/"
        test_results = []

        print("📋 Testing 8-K parsing (first 10 filings)...")
        for i, rec in enumerate(parse_master_idx(idx_text), 1):
            print(f"   [{i}/10] {rec['company']} ({rec['cik']}) - {rec['date']}")

            if not rec["accession"]:
                continue

            filing_index_url = urljoin(base, rec["path"])
            try:
                file_html = get_text(filing_index_url, headers)
                soup = BeautifulSoup(file_html, "html.parser")

                doc_link = soup.find("a", href=True, string=re.compile(r"\.htm(l)?$", re.I))
                doc_url = filing_index_url if not doc_link else urljoin(
                    filing_index_url.rsplit("/", 1)[0] + "/", doc_link["href"]
                )

                has_match, reason = test_scan_filing(doc_url, headers)

                if has_match:
                    print(f"      ✅ POTENTIAL HIT: {reason}")
                    test_results.append((rec, doc_url, reason))
                else:
                    print(f"      ❌ {reason}")

            except Exception as e:
                print(f"      ⚠️  Error: {str(e)}")

        print(f"\n🎯 Test Results:")
        print(f"   Processed: 10 recent 8-K filings")
        print(f"   Potential hits: {len(test_results)}")

        if test_results:
            print(f"\n📄 Hits found:")
            for rec, url, reason in test_results:
                print(f"   • {rec['company']} - {reason}")
                print(f"     {url}")

        print(f"\n✅ Test completed successfully!")
        print(f"   Next step: Configure SMTP settings in .env file")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()