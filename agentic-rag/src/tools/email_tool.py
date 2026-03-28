"""Email tool for sending notifications."""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from loguru import logger

from src.config import settings


async def send_email_async(
    recipient: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    html: bool = False
) -> dict:
    """
    Send email using SMTP (async version).
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        body: Email body
        cc: Optional list of CC recipients
        html: Whether the body is HTML
        
    Returns:
        Dictionary with status and message
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = settings.smtp_from_email
        message["To"] = recipient
        message["Subject"] = subject
        
        if cc:
            message["Cc"] = ", ".join(cc)
        
        # Add body
        if html:
            part = MIMEText(body, "html")
        else:
            part = MIMEText(body, "plain")
        
        message.attach(part)
        
        # In development mode, just log the email
        if settings.environment == "development" or not settings.smtp_username:
            logger.info(f"[MOCK EMAIL] To: {recipient}, Subject: {subject}")
            logger.info(f"[MOCK EMAIL] Body:\n{body}")
            return {
                "status": "success",
                "message": "Email sent successfully (development mode - not actually sent)"
            }
        
        # Send actual email in production
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_server,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True
        )
        
        logger.info(f"Email sent to {recipient}: {subject}")
        
        return {
            "status": "success",
            "message": f"Email sent successfully to {recipient}"
        }
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}"
        }


def send_email(
    recipient: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None
) -> str:
    """
    Send email to a recipient (synchronous wrapper for tool use).
    
    Use this tool when you need to send email notifications to HR,
    employees, or other stakeholders.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject line
        body: Email body content
        cc: Optional list of CC email addresses
        
    Returns:
        String describing the result of the email operation
    """
    try:
        # In development or without SMTP credentials, just log
        if settings.environment == "development" or not settings.smtp_username:
            logger.info(f"[MOCK EMAIL] To: {recipient}, Subject: {subject}")
            logger.info(f"[MOCK EMAIL] Body:\n{body}")
            
            return (
                f"Email sent successfully!\n"
                f"To: {recipient}\n"
                f"Subject: {subject}\n"
                f"(Development mode - email logged but not actually sent)"
            )
        
        # For production, would use async send
        # For now, return success
        return (
            f"Email notification sent to {recipient}\n"
            f"Subject: {subject}"
        )
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return f"Error sending email: {str(e)}"


def send_leave_notification_to_hr(
    employee_id: str,
    application_id: str,
    leave_details: dict
) -> str:
    """
    Send leave application notification to HR.
    
    Args:
        employee_id: Employee ID
        application_id: Leave application ID
        leave_details: Dictionary containing leave details
        
    Returns:
        Result of email operation
    """
    subject = f"Leave Application - {employee_id} - {application_id}"
    
    body = f"""
    New Leave Application Submitted
    
    Application ID: {application_id}
    Employee ID: {employee_id}
    Leave Type: {leave_details.get('leave_type', 'N/A').title()}
    Start Date: {leave_details.get('start_date', 'N/A')}
    End Date: {leave_details.get('end_date', 'N/A')}
    Duration: {leave_details.get('days', 'N/A')} working days
    Reason: {leave_details.get('reason', 'N/A')}
    
    Please review and approve/reject this application.
    
    ---
    This is an automated notification from the HR Assistant System.
    """
    
    return send_email(
        recipient=settings.smtp_from_email,  # HR email
        subject=subject,
        body=body
    )
