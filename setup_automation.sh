#!/bin/bash
# Setup automation for government equity notifier

SCRIPT_DIR="/Users/alext/Documents/Claude"
PYTHON_PATH="/usr/bin/python3"
LOG_FILE="$SCRIPT_DIR/gov_notifier.log"

echo "🚀 Setting up Government Equity Notifier automation..."

# Make sure script is executable
chmod +x "$SCRIPT_DIR/gov_equity_notifier_enhanced.py"

# Create log file if it doesn't exist
touch "$LOG_FILE"

# Create cron job (runs every weekday at 8:05 AM)
CRON_JOB="5 8 * * 1-5 $PYTHON_PATH $SCRIPT_DIR/gov_equity_notifier_enhanced.py >> $LOG_FILE 2>&1"

echo "📅 Adding cron job:"
echo "   $CRON_JOB"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "gov_equity_notifier_enhanced.py"; then
    echo "   ⚠️  Cron job already exists, skipping..."
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "   ✅ Cron job added successfully!"
fi

echo "
📋 Setup Complete!

Next steps:
1. Configure your SMTP settings in: $SCRIPT_DIR/.env
2. Test email functionality:
   $PYTHON_PATH $SCRIPT_DIR/gov_equity_notifier_enhanced.py

Schedule:
- Runs every weekday at 8:05 AM
- Logs to: $LOG_FILE
- Database: $SCRIPT_DIR/gov_equity_seen.sqlite3

To view logs:
  tail -f $LOG_FILE

To remove automation:
  crontab -e  (then delete the gov_equity_notifier line)
"