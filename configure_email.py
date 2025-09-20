#!/usr/bin/env python3
"""
Interactive email configuration helper for government equity notifier.
"""

import os
import sys

def main():
    env_path = "/Users/alext/Documents/Claude/.env"

    print("📧 Email Configuration Helper")
    print("=" * 40)

    print("\nChoose your email provider:")
    print("1. Gmail (with app password)")
    print("2. Fastmail")
    print("3. SendGrid")
    print("4. Custom SMTP")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        smtp_host = "smtp.gmail.com"
        smtp_port = "587"
        print("\n📝 Gmail Setup:")
        print("1. Go to Google Account settings")
        print("2. Enable 2FA if not already enabled")
        print("3. Generate an 'App Password' for Mail")
        print("4. Use that app password below (not your regular password)")

    elif choice == "2":
        smtp_host = "smtp.fastmail.com"
        smtp_port = "587"
        print("\n📝 Fastmail Setup:")
        print("Use your regular Fastmail credentials")

    elif choice == "3":
        smtp_host = "smtp.sendgrid.net"
        smtp_port = "587"
        print("\n📝 SendGrid Setup:")
        print("1. Create free SendGrid account")
        print("2. Create API key in settings")
        print("3. Use 'apikey' as username, API key as password")

    elif choice == "4":
        smtp_host = input("SMTP Host: ").strip()
        smtp_port = input("SMTP Port (usually 587): ").strip() or "587"

    else:
        print("Invalid choice")
        sys.exit(1)

    smtp_user = input(f"\nEmail address for {smtp_host}: ").strip()
    smtp_pass = input("Password/API Key: ").strip()
    from_email = input("From email (can be same as above): ").strip() or smtp_user

    # Create .env content
    env_content = f"""# SEC EDGAR Configuration
SEC_USER_AGENT="Alex Talbott alext@hey.com"

# Email Configuration
SMTP_HOST="{smtp_host}"
SMTP_PORT="{smtp_port}"
SMTP_USER="{smtp_user}"
SMTP_PASS="{smtp_pass}"
FROM_EMAIL="{from_email}"
TO_EMAIL="alext@hey.com"
"""

    # Write .env file
    with open(env_path, "w") as f:
        f.write(env_content)

    print(f"\n✅ Configuration saved to {env_path}")
    print("\n🧪 Test your configuration:")
    print("   cd /Users/alext/Documents/Claude")
    print("   python3 gov_equity_notifier_enhanced.py")

if __name__ == "__main__":
    main()