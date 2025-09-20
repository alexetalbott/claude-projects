#!/usr/bin/env python3
"""
Monitor and manage the government equity notifier.
"""

import os
import sqlite3
from datetime import datetime, timedelta

def show_status():
    """Show current status of the notifier."""
    script_dir = "/Users/alext/Documents/Claude"
    db_path = os.path.join(script_dir, "gov_equity_seen.sqlite3")
    log_path = os.path.join(script_dir, "gov_notifier.log")

    print("📊 Government Equity Notifier Status")
    print("=" * 40)

    # Check database
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT COUNT(*) FROM seen")
        count = cur.fetchone()[0]
        print(f"📄 Filings processed: {count}")

        # Recent high-confidence hits
        cur = conn.execute("""
            SELECT COUNT(*) FROM seen
            WHERE confidence >= 0.7
        """)
        high_conf = cur.fetchone()[0]
        print(f"🎯 High-confidence hits: {high_conf}")
        conn.close()
    else:
        print("📄 Database: Not yet created")

    # Check recent logs
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
            recent_lines = [l.strip() for l in lines[-10:] if l.strip()]

            print(f"\n📝 Recent activity (last 10 lines):")
            for line in recent_lines:
                print(f"   {line}")
        except:
            print("📝 Logs: Unable to read log file")
    else:
        print("📝 Logs: No log file yet")

    # Check cron status
    import subprocess
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if "gov_equity_notifier_enhanced.py" in result.stdout:
            print("⏰ Cron job: ✅ Active (runs weekdays 8:05 AM)")
        else:
            print("⏰ Cron job: ❌ Not found")
    except:
        print("⏰ Cron job: ❓ Unable to check")

def clear_database():
    """Clear the seen filings database."""
    script_dir = "/Users/alext/Documents/Claude"
    db_path = os.path.join(script_dir, "gov_equity_seen.sqlite3")

    if os.path.exists(db_path):
        response = input("⚠️  Clear all seen filings? This will cause re-alerts. (y/N): ")
        if response.lower() == 'y':
            os.remove(db_path)
            print("✅ Database cleared")
        else:
            print("❌ Cancelled")
    else:
        print("📄 No database to clear")

def show_logs():
    """Show recent logs with tail -f like behavior."""
    log_path = "/Users/alext/Documents/Claude/gov_notifier.log"

    if os.path.exists(log_path):
        os.system(f"tail -50 {log_path}")
    else:
        print("📝 No log file found")

def main():
    if len(os.sys.argv) > 1:
        cmd = os.sys.argv[1]
        if cmd == "clear":
            clear_database()
        elif cmd == "logs":
            show_logs()
        else:
            print("Usage: python3 monitor_notifier.py [clear|logs]")
    else:
        show_status()

if __name__ == "__main__":
    main()