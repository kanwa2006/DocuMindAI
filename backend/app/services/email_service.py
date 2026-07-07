import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Send a transactional email via Brevo SMTP. Never raises — logs on failure."""
    if not settings.BREVO_SMTP_USER or not settings.BREVO_SMTP_PASSWORD:
        logger.warning("[email] Brevo SMTP not configured — skipping email to %s", to_email)
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_ADDRESS}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.BREVO_SMTP_HOST, settings.BREVO_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.BREVO_SMTP_USER, settings.BREVO_SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_ADDRESS, [to_email], msg.as_string())

        logger.info("[email] Sent '%s' to %s", subject, to_email)
    except Exception as exc:
        logger.error("[email] Failed to send '%s' to %s: %s", subject, to_email, exc)


def send_welcome_email(user_email: str, user_name: str = None) -> None:
    """Triggered once after email verification to onboard the user."""
    name = user_name or "there"
    subject = "Welcome to DocuMindAI — You're all set!"
    html = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 24px; background: #f9fafb;">
  <div style="background: #fff; border-radius: 12px; padding: 32px; border: 1px solid #e5e7eb;">
    <h2 style="color: #5b4fcf; margin-top: 0;">Welcome to DocuMindAI, {name}! 🎉</h2>
    <p>Your email has been verified and your account is ready to use.</p>
    <p>You have <strong>5 free queries</strong> to explore your documents with AI. Ask anything in natural language — DocuMindAI finds answers grounded in your own files.</p>
    <h3 style="color: #374151;">Getting started in 3 steps:</h3>
    <ol style="line-height: 1.8; color: #4b5563;">
      <li>Upload a PDF, Word doc, or presentation</li>
      <li>Choose your workspace — Legal, Finance, HR, Research...</li>
      <li>Ask your first question</li>
    </ol>
    <div style="margin: 24px 0;">
      <a href="https://documindai.com/dashboard"
         style="display: inline-block; background: #5b4fcf; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: bold;">
        Open DocuMindAI →
      </a>
    </div>
    <p style="color: #9ca3af; font-size: 13px;">
      You're on the free trial plan (5 queries).
      <a href="https://documindai.com/pricing" style="color: #5b4fcf;">Upgrade anytime</a> for unlimited access.
    </p>
  </div>
  <p style="color: #d1d5db; font-size: 11px; text-align: center; margin-top: 16px;">
    DocuMindAI — Document Intelligence for Professionals
  </p>
</body>
</html>
"""
    send_email(user_email, subject, html)


def send_trial_nudge_email(user_email: str, user_name: str = None, queries_used: int = 3) -> None:
    """Triggered at trial_queries_used == 3 — user has 2 queries remaining."""
    name = user_name or "there"
    queries_remaining = 5 - queries_used
    subject = f"You've used {queries_used} of 5 free queries — {queries_remaining} left"
    html = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 24px; background: #f9fafb;">
  <div style="background: #fff; border-radius: 12px; padding: 32px; border: 1px solid #e5e7eb;">
    <h2 style="color: #5b4fcf; margin-top: 0;">Hi {name}, you're getting the hang of it! 🚀</h2>
    <p>You've used <strong>{queries_used} of 5</strong> free queries — <strong>{queries_remaining} remaining</strong>.</p>
    <p>DocuMindAI Pro gives you unlimited queries, priority document processing, and advanced workspace features.</p>
    <div style="background: #f3f0ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
      <strong style="color: #5b4fcf;">What you get with Pro:</strong>
      <ul style="margin: 10px 0 0; line-height: 1.8; color: #4b5563;">
        <li>Unlimited queries across all workspaces</li>
        <li>Priority processing for large documents</li>
        <li>Advanced export formats (PDF, Word, Excel)</li>
        <li>Full session history and bookmarks</li>
      </ul>
    </div>
    <a href="https://documindai.com/upgrade"
       style="display: inline-block; background: #5b4fcf; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-bottom: 16px;">
      Upgrade to Pro →
    </a>
    <p style="color: #9ca3af; font-size: 13px;">
      Or keep exploring — you still have {queries_remaining} free {'query' if queries_remaining == 1 else 'queries'} left.
    </p>
  </div>
  <p style="color: #d1d5db; font-size: 11px; text-align: center; margin-top: 16px;">
    DocuMindAI — Document Intelligence for Professionals
  </p>
</body>
</html>
"""
    send_email(user_email, subject, html)


def send_upgrade_reminder_email(user_email: str, user_name: str = None) -> None:
    """Triggered at trial_queries_used == 4 — user has 1 query remaining."""
    name = user_name or "there"
    subject = "1 free query left — Don't lose your momentum"
    html = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 24px; background: #f9fafb;">
  <div style="background: #fff; border-radius: 12px; padding: 32px; border: 1px solid #fee2e2;">
    <h2 style="color: #dc2626; margin-top: 0;">Hi {name}, this is your last free query ⚠️</h2>
    <p>You've used <strong>4 of 5</strong> free queries. After your next query, you'll need to upgrade to continue using DocuMindAI.</p>
    <div style="background: #fef2f2; border-radius: 8px; padding: 16px; margin: 20px 0; border: 1px solid #fecaca;">
      <strong style="color: #dc2626;">Upgrade now and keep going:</strong>
      <ul style="margin: 10px 0 0; line-height: 1.8; color: #4b5563;">
        <li>Unlimited queries across all workspaces</li>
        <li>Priority document processing</li>
        <li>Advanced export formats (PDF, Word, Excel)</li>
        <li>Full session history and bookmarks</li>
      </ul>
    </div>
    <a href="https://documindai.com/upgrade"
       style="display: inline-block; background: #dc2626; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-bottom: 16px;">
      Upgrade Now — Keep Going →
    </a>
    <p style="color: #9ca3af; font-size: 13px;">
      Questions? Reply to this email or visit
      <a href="https://documindai.com/pricing" style="color: #5b4fcf;">our pricing page</a>.
    </p>
  </div>
  <p style="color: #d1d5db; font-size: 11px; text-align: center; margin-top: 16px;">
    DocuMindAI — Document Intelligence for Professionals
  </p>
</body>
</html>
"""
    send_email(user_email, subject, html)
