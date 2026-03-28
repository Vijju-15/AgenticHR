"""Real email delivery service for AgenticHR.

Uses SMTP (Gmail App Password, or any SMTP provider).
All credentials come from environment variables — never hardcoded.

Required .env vars:
    SMTP_HOST       default: smtp.gmail.com
    SMTP_PORT       default: 587
    SMTP_USER       your Gmail address (or SMTP username)
    SMTP_PASSWORD   Gmail App Password (NOT your real Gmail password)
    SMTP_FROM_NAME  default: AgenticHR
    SMTP_ENABLED    set to "true" to send real emails (default: false → logs only)
"""

from __future__ import annotations

import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional

from loguru import logger


# ── Config from env ───────────────────────────────────────────────────────

SMTP_HOST      = os.getenv("SMTP_HOST",      "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT",  "587"))
SMTP_USER      = os.getenv("SMTP_USER",      "")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD",  "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AgenticHR")
SMTP_ENABLED   = os.getenv("SMTP_ENABLED",   "false").lower() == "true"
APP_BASE_URL   = os.getenv("APP_BASE_URL",   "http://localhost:3000")


# ── Core send function ────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Send an email.

    Returns True on success, False on failure.
    If SMTP_ENABLED=false, logs the email instead of sending (safe for dev/test).
    """
    if not SMTP_ENABLED:
        logger.info(
            f"[EMAIL MOCK] To: {to_email} | Subject: {subject}\n"
            f"Body preview: {text_body[:200] if text_body else html_body[:200]}"
        )
        return True

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP_USER/SMTP_PASSWORD not set — skipping email send")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg["To"]      = to_email
        msg["Message-ID"] = f"<{uuid.uuid4().hex}@agentichr>"

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


# ── Email templates ───────────────────────────────────────────────────────

def send_offer_letter(
    candidate_email: str,
    candidate_name: str,
    role: str,
    department: str,
    joining_date: str,
    stipend: str,
    acceptance_token: str,
    company_name: str = "Acme Corp",
) -> bool:
    acceptance_url = f"{APP_BASE_URL}/offer/{acceptance_token}"
    subject = f"🎉 Offer Letter — {role} at {company_name}"
    html = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f9f9f9;padding:32px;">
<div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:40px;border:1px solid #e5e7eb;">
  <h1 style="color:#059669;margin-bottom:4px;">Congratulations, {candidate_name}!</h1>
  <p style="color:#6b7280;margin-top:0;">We are thrilled to offer you a position at {company_name}.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:8px 0;color:#6b7280;width:40%;">Role</td><td style="padding:8px 0;font-weight:600;color:#111827;">{role}</td></tr>
    <tr><td style="padding:8px 0;color:#6b7280;">Department</td><td style="padding:8px 0;font-weight:600;color:#111827;">{department}</td></tr>
    <tr><td style="padding:8px 0;color:#6b7280;">Joining Date</td><td style="padding:8px 0;font-weight:600;color:#111827;">{joining_date}</td></tr>
    <tr><td style="padding:8px 0;color:#6b7280;">Compensation</td><td style="padding:8px 0;font-weight:600;color:#111827;">{stipend}</td></tr>
  </table>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#374151;">Please review and formally accept your offer by clicking the button below.
  This offer expires in <strong>3 days</strong>.</p>
  <div style="text-align:center;margin:32px 0;">
    <a href="{acceptance_url}"
       style="background:#059669;color:#fff;padding:14px 32px;border-radius:8px;
              text-decoration:none;font-weight:600;font-size:16px;">
      View &amp; Accept Offer
    </a>
  </div>
  <p style="color:#9ca3af;font-size:13px;">
    Or copy this link: {acceptance_url}
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#6b7280;font-size:13px;">
    If you have any questions, reply to this email or contact your HR team.
  </p>
  <p style="color:#6b7280;font-size:13px;">— The {company_name} HR Team</p>
</div>
</body></html>
"""
    text = (
        f"Congratulations {candidate_name}!\n\n"
        f"Role: {role}\nDepartment: {department}\nJoining Date: {joining_date}\n"
        f"Compensation: {stipend}\n\n"
        f"Accept your offer here: {acceptance_url}\n\n"
        f"This offer expires in 3 days.\n\n— {company_name} HR Team"
    )
    return send_email(candidate_email, subject, html, text)


def send_document_request(
    candidate_email: str,
    candidate_name: str,
    workflow_id: str,
    company_name: str = "Acme Corp",
) -> bool:
    upload_url = f"{APP_BASE_URL}/documents/upload/{workflow_id}"
    subject = f"📄 Action Required: Submit Your Joining Documents — {company_name}"
    html = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f9f9f9;padding:32px;">
<div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:40px;border:1px solid #e5e7eb;">
  <h1 style="color:#059669;">Hi {candidate_name},</h1>
  <p style="color:#374151;">
    Thank you for accepting your offer. To complete your onboarding, please upload the following documents:
  </p>
  <ul style="color:#374151;line-height:2;">
    <li>Government-issued Photo ID (Aadhaar / Passport / PAN Card)</li>
    <li>Recent Passport-size Photograph</li>
    <li>Educational Qualification Certificates (Marksheets / Degree)</li>
    <li>Any other certificates or documents specified in your offer letter</li>
  </ul>
  <div style="text-align:center;margin:32px 0;">
    <a href="{upload_url}"
       style="background:#059669;color:#fff;padding:14px 32px;border-radius:8px;
              text-decoration:none;font-weight:600;font-size:16px;">
      Upload Documents
    </a>
  </div>
  <p style="color:#9ca3af;font-size:13px;">Link: {upload_url}</p>
  <p style="color:#6b7280;font-size:13px;">
    Please upload all documents before your joining date. If you face any issues, contact HR.
  </p>
  <p style="color:#6b7280;font-size:13px;">— The {company_name} HR Team</p>
</div>
</body></html>
"""
    text = (
        f"Hi {candidate_name},\n\n"
        f"Please upload your joining documents here: {upload_url}\n\n"
        f"Required documents:\n"
        f"- Government-issued Photo ID\n- Passport-size Photograph\n"
        f"- Educational Certificates\n\n"
        f"— {company_name} HR Team"
    )
    return send_email(candidate_email, subject, html, text)


def send_manager_introduction(
    candidate_email: str,
    candidate_name: str,
    manager_name: str,
    manager_email: str,
    team_name: str,
    joining_date: str,
    company_name: str = "Acme Corp",
) -> bool:
    subject = f"👋 Meet Your Manager — {manager_name} | {company_name}"
    html = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f9f9f9;padding:32px;">
<div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:40px;border:1px solid #e5e7eb;">
  <h1 style="color:#059669;">Hi {candidate_name},</h1>
  <p style="color:#374151;">
    We're excited to introduce you to your team! Here are your team details for when you join on <strong>{joining_date}</strong>:
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:8px 0;color:#6b7280;width:40%;">Your Manager</td><td style="padding:8px 0;font-weight:600;color:#111827;">{manager_name}</td></tr>
    <tr><td style="padding:8px 0;color:#6b7280;">Manager Email</td><td style="padding:8px 0;color:#059669;">{manager_email}</td></tr>
    <tr><td style="padding:8px 0;color:#6b7280;">Team</td><td style="padding:8px 0;font-weight:600;color:#111827;">{team_name}</td></tr>
  </table>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#374151;">
    Feel free to reach out to {manager_name} at <a href="mailto:{manager_email}" style="color:#059669;">{manager_email}</a>
    before your first day with any questions!
  </p>
  <p style="color:#374151;">We look forward to seeing you on <strong>{joining_date}</strong>. 🎉</p>
  <p style="color:#6b7280;font-size:13px;">— The {company_name} HR Team</p>
</div>
</body></html>
"""
    text = (
        f"Hi {candidate_name},\n\n"
        f"Your Manager: {manager_name} ({manager_email})\nTeam: {team_name}\n"
        f"Joining Date: {joining_date}\n\n"
        f"Feel free to reach out to your manager before your first day.\n\n"
        f"— {company_name} HR Team"
    )
    return send_email(candidate_email, subject, html, text)


def send_welcome_credentials(
    candidate_email: str,
    candidate_name: str,
    company_email: str,
    temp_password: str,
    role: str,
    tools: list[str] | None = None,
    company_name: str = "Acme Corp",
) -> bool:
    if tools is None:
        tools = ["Slack", "Jira", "GitHub", "Google Workspace"]
    tools_html = "".join(f"<li style='line-height:2;color:#374151;'>{t}</li>" for t in tools)
    subject = f"🔐 Your {company_name} Login Credentials"
    html = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f9f9f9;padding:32px;">
<div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:40px;border:1px solid #e5e7eb;">
  <h1 style="color:#059669;">Welcome to {company_name}, {candidate_name}!</h1>
  <p style="color:#374151;">Here are your login credentials. Please change your password after first login.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:20px;margin:16px 0;">
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:6px 0;color:#6b7280;width:40%;">Company Email</td><td style="padding:6px 0;font-weight:600;color:#111827;">{company_email}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">Temporary Password</td><td style="padding:6px 0;font-weight:600;color:#dc2626;letter-spacing:1px;">{temp_password}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;">Role</td><td style="padding:6px 0;color:#111827;">{role}</td></tr>
    </table>
  </div>
  <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:16px;margin:16px 0;">
    <strong style="color:#ea580c;">⚠️ Important:</strong>
    <span style="color:#374151;"> Change your password immediately after your first login.</span>
  </div>
  <p style="color:#374151;font-weight:600;">You will have access to:</p>
  <ul>{tools_html}</ul>
  <p style="color:#6b7280;font-size:13px;">
    If you have trouble logging in, contact your HR team or IT support.
  </p>
  <p style="color:#6b7280;font-size:13px;">— The {company_name} HR Team</p>
</div>
</body></html>
"""
    text = (
        f"Welcome to {company_name}, {candidate_name}!\n\n"
        f"Company Email: {company_email}\nTemporary Password: {temp_password}\n\n"
        f"IMPORTANT: Change your password after first login.\n\n"
        f"Tools access: {', '.join(tools)}\n\n"
        f"— {company_name} HR Team"
    )
    return send_email(candidate_email, subject, html, text)


def send_meeting_invite(
    personal_email: str,
    intern_name: str,
    meeting_title: str,
    start_datetime: str,
    end_datetime: str,
    meet_link: str,
    calendar_url: str = "",
    hr_email: str = "",
    company_name: str = "Acme Corp",
) -> bool:
    """Send a Google Meet invite notification to the intern's personal email."""
    subject = f"Meeting Invitation: {meeting_title}"
    meet_button = (
        f'<a href="{meet_link}" style="background:#1a73e8;color:#fff;padding:12px 28px;'
        f'border-radius:6px;text-decoration:none;font-weight:600;font-size:15px;">'
        f'Join Google Meet</a>'
    ) if meet_link else ""
    cal_link = (
        f'<p style="margin-top:12px;"><a href="{calendar_url}" style="color:#1a73e8;">'
        f'View in Google Calendar</a></p>'
    ) if calendar_url else ""
    organiser_row = f'<p style="margin:4px 0;"><b>Organiser:</b> {hr_email}</p>' if hr_email else ""
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:32px;">
<div style="max-width:580px;margin:auto;background:#fff;border-radius:12px;padding:40px;border:1px solid #e5e7eb;">
  <h2 style="color:#1a1a2e">Meeting Invitation</h2>
  <p style="color:#374151;">Hi {intern_name},</p>
  <p style="color:#374151;">You have a new meeting scheduled:</p>
  <div style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px;border-radius:4px;margin:20px 0;">
    <p style="margin:4px 0;"><b>Title:</b> {meeting_title}</p>
    <p style="margin:4px 0;"><b>Start:</b> {start_datetime}</p>
    <p style="margin:4px 0;"><b>End:</b>   {end_datetime}</p>
    {organiser_row}
  </div>
  <div style="text-align:center;margin:28px 0;">{meet_button}</div>
  {cal_link}
  <p style="color:#9ca3af;font-size:13px;">— The {company_name} HR Team</p>
</div></body></html>"""
    text = (
        f"Meeting Invitation: {meeting_title}\n\n"
        f"Start: {start_datetime}\nEnd: {end_datetime}\n"
        f"Join Meet: {meet_link}\n"
    )
    return send_email(personal_email, subject, html, text)
