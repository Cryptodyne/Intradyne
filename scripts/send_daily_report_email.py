# Daily Report Email Sender
"""Send daily paper trading report via email.

Configuration:
- Edit EMAIL_CONFIG below with your email settings
- For Gmail: Use App Password (not your regular password)
  Generate at: https://myaccount.google.com/apppasswords

Usage:
  python scripts/send_daily_report_email.py
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import glob

# ============================================================================
# EMAIL CONFIGURATION - EDIT THESE SETTINGS
# ============================================================================

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Gmail SMTP server
    'smtp_port': 587,                  # TLS port
    'sender_email': 'your-email@gmail.com',  # Your email
    'sender_password': 'your-app-password',   # Gmail App Password (not regular password!)
    'recipient_email': 'your-email@gmail.com',  # Where to send the report
}

# ============================================================================


def send_daily_report():
    """Send today's paper trading report via email."""
    
    print("\n" + "="*70)
    print("📧 DAILY REPORT EMAIL SENDER")
    print("="*70 + "\n")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Find today's report
    report_path = f'reports/daily/daily_report_{today_str}.md'
    
    if not os.path.exists(report_path):
        print(f"❌ No report found for today: {report_path}")
        print("   Generate it first: python scripts/generate_daily_report.py")
        return False
    
    # Find chart images
    charts_dir = 'reports/daily/charts'
    chart_files = []
    if os.path.exists(charts_dir):
        chart_files = glob.glob(os.path.join(charts_dir, f'*_{today_str}.png'))
    
    print(f"✅ Found report: {report_path}")
    print(f"✅ Found {len(chart_files)} charts")
    
    # Read report content
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = EMAIL_CONFIG['recipient_email']
    msg['Subject'] = f"📊 Intradyne Daily Paper Trading Report - {today_str}"
    
    # Create HTML version (for better formatting)
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #1a1a1a; color: #ffffff; padding: 20px;">
        <h1 style="color: #00ff41;">📊 Intradyne Daily Report</h1>
        <p><strong>Date:</strong> {today_str}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr style="border-color: #00ff41;">
        <pre style="background-color: #2a2a2a; padding: 15px; border-radius: 5px; overflow-x: auto;">
{report_content}
        </pre>
        <hr style="border-color: #00ff41;">
        <p style="color: #888;">
          <em>This is an automated report from your Intradyne Paper Trading System</em>
        </p>
      </body>
    </html>
    """
    
    # Attach HTML
    msg.attach(MIMEText(html_content, 'html'))
    
    # Attach markdown file
    with open(report_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="daily_report_{today_str}.md"')
        msg.attach(part)
    
    # Attach chart images
    for chart_file in chart_files:
        with open(chart_file, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(chart_file)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)
    
    # Send email
    try:
        print(f"\n📤 Sending email to {EMAIL_CONFIG['recipient_email']}...")
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully!")
        print(f"   Report: {report_path}")
        print(f"   Charts: {len(chart_files)} attached")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("\n❌ Email authentication failed!")
        print("   For Gmail, you need an App Password:")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Generate a new app password")
        print("   3. Update EMAIL_CONFIG in this script")
        return False
        
    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    
    # Check if email is configured
    if EMAIL_CONFIG['sender_email'] == 'your-email@gmail.com':
        print("\n❌ Email not configured!")
        print("\nPlease edit this script and update EMAIL_CONFIG:")
        print("  1. Set sender_email (your Gmail address)")
        print("  2. Set sender_password (Gmail App Password)")
        print("  3. Set recipient_email (where to send the report)")
        print("\n💡 To get Gmail App Password:")
        print("   https://myaccount.google.com/apppasswords\n")
        return
    
    success = send_daily_report()
    
    if success:
        print("\n✅ Daily report email sent successfully!\n")
    else:
        print("\n❌ Failed to send daily report email\n")


if __name__ == "__main__":
    main()
