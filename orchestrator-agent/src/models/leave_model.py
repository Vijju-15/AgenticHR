"""MongoDB document models for leave requests and employee profiles."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class LeaveStatus(str, Enum):
    """Leave request status."""
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    CANCELLED = "CANCELLED"


class LeaveType(str, Enum):
    """Leave types."""
    CASUAL  = "casual"
    SICK    = "sick"
    EARNED  = "earned"
    UNPAID  = "unpaid"


def leave_request_to_dict(
    request_id: str,
    tenant_id: str,
    employee_id: str,
    employee_name: str,
    employee_email: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    num_days: float,
    reason: str,
    status: LeaveStatus = LeaveStatus.PENDING,
    hr_email: Optional[str] = None,
    approver_id: Optional[str] = None,
    approver_note: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert leave request data to MongoDB document."""
    now = datetime.now(timezone.utc)
    return {
        "request_id":     request_id,
        "tenant_id":      tenant_id,
        "employee_id":    employee_id,
        "employee_name":  employee_name,
        "employee_email": employee_email,
        "leave_type":     leave_type,
        "start_date":     start_date,
        "end_date":       end_date,
        "num_days":       num_days,
        "reason":         reason,
        "status":         status.value if isinstance(status, LeaveStatus) else status,
        "hr_email":       hr_email,
        "approver_id":    approver_id,
        "approver_note":  approver_note,
        "created_at":     now,
        "updated_at":     now,
        "decided_at":     None,
        "metadata":       metadata or {},
    }
