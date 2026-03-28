"""HR Approval Tools for Guide Agent.

These tools allow the Guide Agent to:
1. Submit leave requests to the Orchestrator for HR approval
2. Check the status of submitted leave requests
3. Get employee onboarding journey progress

The Guide Agent uses these tools as part of end-to-end autonomous task completion.
"""

from __future__ import annotations

import os
import httpx
from typing import Optional
from loguru import logger

# Orchestrator base URL (configurable via env)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_AGENT_URL", "http://localhost:8001")
_TIMEOUT = 10


def submit_leave_request(
    employee_id: str,
    employee_name: str,
    employee_email: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    num_days: float,
    reason: str,
    company_id: str,
    hr_email: Optional[str] = None,
) -> str:
    """
    Submit a leave request to HR for approval.

    Use this tool AFTER:
    1. Verifying leave policy (query_company_policy)
    2. Confirming the employee has sufficient leave balance (check_leave_balance)

    This tool sends the request to the HR queue. The employee will be notified
    once HR approves or rejects it.

    Args:
        employee_id:    Employee's ID (e.g. "EMP001")
        employee_name:  Full name of the employee
        employee_email: Employee's work email
        leave_type:     One of: casual, sick, earned, unpaid
        start_date:     Leave start date in YYYY-MM-DD format
        end_date:       Leave end date in YYYY-MM-DD format (same as start for single day)
        num_days:       Number of leave days requested (can be 0.5 for half-day)
        reason:         Brief reason for the leave
        company_id:     Company / tenant identifier
        hr_email:       HR manager email for notification (optional)

    Returns:
        Confirmation message with the leave request ID
    """
    payload = {
        "tenant_id":      company_id,
        "employee_id":    employee_id,
        "employee_name":  employee_name,
        "employee_email": employee_email,
        "leave_type":     leave_type,
        "start_date":     start_date,
        "end_date":       end_date,
        "num_days":       float(num_days),
        "reason":         reason,
        "hr_email":       hr_email,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{ORCHESTRATOR_URL}/leave/requests", json=payload)
            resp.raise_for_status()
            data = resp.json()

        request_id = data.get("request_id", "N/A")
        logger.info(f"Leave request {request_id} submitted for {employee_name}")
        return (
            f"✅ Leave request submitted successfully!\n"
            f"  Request ID  : {request_id}\n"
            f"  Status      : Pending HR Approval\n"
            f"  Employee    : {employee_name}\n"
            f"  Leave Type  : {leave_type}\n"
            f"  Dates       : {start_date} → {end_date} ({num_days} day(s))\n"
            f"  Reason      : {reason}\n\n"
            f"HR will review your request and you will receive a notification "
            f"once it has been approved or rejected."
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error submitting leave request: {e.response.text}")
        return f"❌ Failed to submit leave request: {e.response.text}"
    except Exception as e:
        logger.error(f"Error submitting leave request: {e}")
        return (
            f"⚠️  Could not connect to the HR system right now. "
            f"Please try again later or contact HR directly.\nError: {str(e)}"
        )


def check_leave_request_status(request_id: str) -> str:
    """
    Check the current status of a submitted leave request.

    Use this when an employee asks about the status of their existing leave request.

    Args:
        request_id: The leave request ID (e.g. "LR_acme_corp_a1b2c3d4")

    Returns:
        Current status and details of the leave request
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{ORCHESTRATOR_URL}/leave/requests/{request_id}")
            resp.raise_for_status()
            data = resp.json()

        status      = data.get("status", "UNKNOWN")
        note        = data.get("approver_note") or "No note provided"
        decided_at  = data.get("decided_at") or "Not yet decided"

        status_icon = {"APPROVED": "✅", "REJECTED": "❌", "PENDING": "⏳", "CANCELLED": "🚫"}.get(status, "•")

        return (
            f"{status_icon} Leave Request Status: {status}\n"
            f"  Request ID   : {request_id}\n"
            f"  Employee     : {data.get('employee_name')}\n"
            f"  Leave Type   : {data.get('leave_type')}\n"
            f"  Dates        : {data.get('start_date')} → {data.get('end_date')} "
            f"({data.get('num_days')} day(s))\n"
            f"  HR Note      : {note}\n"
            f"  Decision On  : {decided_at}"
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No leave request found with ID: {request_id}"
        return f"Error fetching leave request: {e.response.text}"
    except Exception as e:
        return f"Could not fetch leave request status. Error: {str(e)}"


def get_my_leave_requests(employee_id: str, company_id: str) -> str:
    """
    Retrieve all leave requests submitted by a specific employee.

    Args:
        employee_id: Employee's ID
        company_id:  Company / tenant identifier

    Returns:
        Formatted list of leave requests with their statuses
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{ORCHESTRATOR_URL}/leave/requests",
                params={"tenant_id": company_id, "employee_id": employee_id},
            )
            resp.raise_for_status()
            data = resp.json()

        requests = data.get("leave_requests", [])
        if not requests:
            return f"No leave requests found for employee {employee_id}."

        lines = [f"📋 Leave Requests for {employee_id} ({len(requests)} found):\n"]
        for r in requests:
            icon = {"APPROVED": "✅", "REJECTED": "❌", "PENDING": "⏳", "CANCELLED": "🚫"}.get(r.get("status"), "•")
            lines.append(
                f"  {icon} [{r.get('request_id')}] {r.get('leave_type')} | "
                f"{r.get('start_date')} → {r.get('end_date')} ({r.get('num_days')} day) | "
                f"{r.get('status')}"
            )
        return "\n".join(lines)

    except Exception as e:
        return f"Could not fetch leave requests. Error: {str(e)}"
