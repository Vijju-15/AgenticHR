"""Minimal SMTP email utility for the Provisioning Agent.

Controlled by the same env vars used by the Orchestrator email service:
  SMTP_ENABLED   - "true" to actually send, anything else = log only (safe for dev)
  SMTP_HOST      - e.g. smtp.gmail.com
  SMTP_PORT      - e.g. 587
  SMTP_USER      - sender email address
  SMTP_PASSWORD  - SMTP / Gmail App-Password
  APP_BASE_URL   - base URL of the frontend, e.g. http://localhost:3000
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Low-level SMTP sender. Returns True on success."""
    enabled = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info(
            f"[EMAIL LOG — SMTP_ENABLED=false]\n"
            f"  To:      {to_email}\n"
            f"  Subject: {subject}\n"
        )
        return True  # treat as success in dev mode

    host     = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port     = int(os.getenv("SMTP_PORT", "587"))
    user     = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    if not user or not password:
        logger.error("SMTP_USER or SMTP_PASSWORD not set — cannot send email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = user
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_welcome_credentials(
    employee_email: str,
    employee_name: str,
    employee_id: str,
    role: str,
    department: str,
    temp_password: str,
) -> bool:
    """Send welcome credentials email to new hire."""
    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
    subject  = "Welcome to AgenticHR — Your Login Credentials"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:24px">
    <div style="max-width:520px;margin:auto;background:#fff;border-radius:8px;padding:32px">
      <h2 style="color:#1a1a2e">Welcome to the Team, {employee_name}! 🎉</h2>
      <p>Your employee profile has been set up. Here are your login details:</p>
      <div style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px;border-radius:4px;margin:16px 0">
        <p><b>Employee ID:</b> {employee_id}</p>
        <p><b>Role:</b> {role}</p>
        <p><b>Department:</b> {department}</p>
        <p><b>Temporary Password:</b> <code style="background:#e8f0fe;padding:2px 6px">{temp_password}</code></p>
      </div>
      <p>Please log in at <a href="{base_url}">{base_url}</a> and change your password immediately.</p>
      <p style="color:#888;font-size:12px">This is an automated message from AgenticHR.</p>
    </div>
    </body></html>
    """
    return _send_email(employee_email, subject, html)


def send_manager_introduction(
    candidate_email: str,
    candidate_name: str,
    role: str,
    department: str,
    manager_name: str,
    manager_email: str,
    joining_date: str,
) -> bool:
    """Send manager introduction email to new hire."""
    subject = f"Meet Your Manager — {manager_name} | AgenticHR"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:24px">
    <div style="max-width:520px;margin:auto;background:#fff;border-radius:8px;padding:32px">
      <h2 style="color:#1a1a2e">Hi {candidate_name}, Meet Your Manager!</h2>
      <p>We're excited to introduce you to your reporting manager before your first day.</p>
      <div style="background:#f0fff4;border-left:4px solid #34a853;padding:16px;border-radius:4px;margin:16px 0">
        <p><b>Manager:</b> {manager_name}</p>
        <p><b>Manager Email:</b> <a href="mailto:{manager_email}">{manager_email}</a></p>
        <p><b>Your Role:</b> {role}</p>
        <p><b>Department:</b> {department}</p>
        <p><b>Joining Date:</b> {joining_date}</p>
      </div>
      <p>Feel free to reach out to {manager_name} before Day 1 if you have any questions.</p>
      <p style="color:#888;font-size:12px">This is an automated message from AgenticHR.</p>
    </div>
    </body></html>
    """
    return _send_email(candidate_email, subject, html)
