# Government Equity Investment Notifier - Setup Guide

## Overview
Automated system to monitor SEC EDGAR 8-K filings for U.S. government equity investments and email alerts to `alext@hey.com`.

## Project Structure
```
/Users/alext/Documents/Claude/
├── gov_equity_notifier_enhanced.py  # Main script with enhanced filtering
├── setup_automation.sh              # Cron job setup
├── monitor_notifier.py              # Status monitoring
├── configure_email.py               # Email setup helper
├── test_gov_notifier.py             # Testing script
├── .env                             # Configuration file
├── gov_equity_seen.sqlite3          # Database (created after first run)
├── gov_notifier.log                 # Log file (created after first run)
└── SETUP_GUIDE.md                   # This file
```

## Enhanced Features
- ✅ Confidence scoring (HIGH ≥0.7, MEDIUM ≥0.4)
- ✅ False positive filtering (excludes risk factors, hypotheticals)
- ✅ Specific government entities (CFIUS, CHIPS Act, DOD, DOC)
- ✅ Transaction indicators (dollar amounts, agreement language)
- ✅ Tighter proximity matching (150 chars vs 220)
- ✅ Email prioritization (high-confidence alerts first)

## Setup Instructions

### Step 1: SendGrid Email Setup (Required)

#### 1.1 Create SendGrid Account
1. Go to [sendgrid.com](https://sendgrid.com)
2. Sign up for free account (100 emails/day limit)
3. Complete email verification

#### 1.2 Create API Key
1. Login to SendGrid dashboard
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Name: "EDGAR Notifier"
5. Select **Restricted Access**
6. Under **Mail Send** → select **Full Access**
7. Click **Create & View**
8. **IMPORTANT**: Copy the API key (starts with `SG.`) - you can't see it again!

#### 1.3 Configure Environment
Edit `/Users/alext/Documents/Claude/.env`:
```bash
# Replace YOUR_SENDGRID_API_KEY_HERE with your actual API key
SMTP_PASS="SG.your_actual_api_key_here"
```

### Step 2: Set Up Automation

#### 2.1 Run Setup Script
```bash
cd /Users/alext/Documents/Claude
./setup_automation.sh
```

This will:
- Set file permissions
- Create log file
- Add cron job (runs weekdays at 8:05 AM)

#### 2.2 Verify Cron Job
```bash
crontab -l
# Should show: 5 8 * * 1-5 /usr/bin/python3 /Users/alext/Documents/Claude/gov_equity_notifier_enhanced.py >> /Users/alext/Documents/Claude/gov_notifier.log 2>&1
```

### Step 3: Test Everything

#### 3.1 Test Script Manually
```bash
cd /Users/alext/Documents/Claude
python3 gov_equity_notifier_enhanced.py
```

Expected outputs:
- `[info] No new high-confidence govt-equity hits today.` (normal)
- `[info] Emailed X hit(s) to alext@hey.com` (if matches found)
- `[error]` messages indicate configuration issues

#### 3.2 Check Status
```bash
python3 monitor_notifier.py          # Show overall status
python3 monitor_notifier.py logs     # View recent logs
```

## Monitoring & Management

### View Status
```bash
cd /Users/alext/Documents/Claude
python3 monitor_notifier.py
```

### View Logs
```bash
python3 monitor_notifier.py logs
# OR
tail -f gov_notifier.log
```

### Clear Database (Re-enable alerts for seen filings)
```bash
python3 monitor_notifier.py clear
```

### Remove Automation
```bash
crontab -e
# Delete the line containing "gov_equity_notifier_enhanced.py"
```

## Troubleshooting

### Common Issues

#### "403 Client Error: Forbidden"
- SEC blocking requests due to User-Agent
- Script automatically tries recent business days
- Should resolve automatically

#### "Email send failed"
- Check SendGrid API key in `.env` file
- Verify SendGrid account is verified
- Check SendGrid dashboard for sending limits

#### "No new hits"
- Normal behavior most days
- Government equity investments are rare
- Database prevents duplicate alerts

#### "crontab: command not found"
- Run manually: `python3 gov_equity_notifier_enhanced.py`
- Or set up your own scheduler

### Manual Testing
```bash
# Test without email (for debugging)
cd /Users/alext/Documents/Claude
python3 test_gov_notifier.py
```

## Configuration Details

### Environment Variables (.env)
```bash
SEC_USER_AGENT="Alex Talbott alext@hey.com"     # Required by SEC
SMTP_HOST="smtp.sendgrid.net"                   # SendGrid SMTP
SMTP_PORT="587"                                 # Standard port
SMTP_USER="apikey"                              # Always "apikey" for SendGrid
SMTP_PASS="SG.your_api_key_here"               # Your SendGrid API key
FROM_EMAIL="edgar-alerts@yourdomain.com"       # Can be anything
TO_EMAIL="alext@hey.com"                       # Where alerts go
```

### Detection Patterns

#### Government Entities
- U.S. Government, Department of Commerce/Defense
- CHIPS Act, CFIUS, Defense Production Act
- DOD, DOC, Treasury Department

#### Investment Terms
- equity investment/stake/position
- preferred stock/shares, warrant agreement
- investment/purchase/funding agreement

#### Transaction Indicators
- Dollar amounts with investment/funding
- Agreement execution language
- Tranche/closing/completion terms

### Schedule
- **When**: Weekdays at 8:05 AM
- **What**: Scans previous business day's 8-K filings
- **Output**: High-confidence alerts emailed immediately

---

## Catch-Up Prompt

If you need to catch Claude up to speed on this project, send this prompt:

```
I have a government equity investment monitoring system set up in /Users/alext/Documents/Claude/.

The system:
- Monitors SEC EDGAR 8-K filings for U.S. government equity investments
- Uses enhanced filtering to reduce false positives (confidence scoring, proximity matching)
- Sends email alerts to alext@hey.com via SendGrid SMTP
- Runs daily via cron job at 8:05 AM weekdays
- Uses SQLite database to track seen filings

Key files:
- gov_equity_notifier_enhanced.py (main script)
- .env (SendGrid configuration)
- monitor_notifier.py (status/management)
- setup_automation.sh (cron setup)

Current status: [DESCRIBE CURRENT ISSUE OR QUESTION]

The system was designed to catch actual government equity stakes (CHIPS Act funding, DOD investments, etc.) while filtering out false positives from risk factor discussions and hypothetical scenarios.
```

---

## Next Steps After Setup

1. **Wait for first run** (next weekday 8:05 AM)
2. **Check logs**: `python3 monitor_notifier.py logs`
3. **Monitor email** for alerts at `alext@hey.com`
4. **Verify database growth**: `python3 monitor_notifier.py`

The system will learn and improve over time as it processes more filings and builds its database of seen documents.