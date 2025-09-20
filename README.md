# Claude Projects

Collection of automation scripts and tools built with Claude Code assistance.

## Projects

### 🏛️ Government Equity Investment Notifier

Automated monitoring system for U.S. government equity investments disclosed in SEC EDGAR 8-K filings.

**Features:**
- Enhanced false positive filtering with confidence scoring
- Daily automated scanning via cron job
- Email alerts for high-confidence matches
- SQLite database for duplicate prevention

**Files:**
- `gov_equity_notifier_enhanced.py` - Main monitoring script
- `setup_automation.sh` - Automated cron job setup
- `monitor_notifier.py` - Status monitoring and management
- `configure_email.py` - Email configuration helper
- `SETUP_GUIDE.md` - Complete setup instructions

**Quick Start:**
```bash
# Set up email (SendGrid)
python3 configure_email.py

# Install automation
./setup_automation.sh

# Monitor status
python3 monitor_notifier.py
```

See `SETUP_GUIDE.md` for detailed instructions.

---

*This repository serves as a collection point for various automation projects and Claude-assisted development work.*