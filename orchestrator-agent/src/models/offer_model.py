"""MongoDB document models for offer letters."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class OfferStatus(str, Enum):
    PENDING_ACCEPTANCE = "PENDING_ACCEPTANCE"
    ACCEPTED           = "ACCEPTED"
    DECLINED           = "DECLINED"
    EXPIRED            = "EXPIRED"
    WITHDRAWN          = "WITHDRAWN"


def offer_letter_to_dict(
    offer_id: str,
    tenant_id: str,
    workflow_id: str,
    employee_id: str,
    candidate_name: str,
    candidate_email: str,
    role: str,
    department: str,
    joining_date: str,
    stipend: str,
    acceptance_token: str,
    status: OfferStatus = OfferStatus.PENDING_ACCEPTANCE,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert offer letter data to a MongoDB document."""
    now = datetime.now(timezone.utc)
    return {
        "offer_id":         offer_id,
        "tenant_id":        tenant_id,
        "workflow_id":      workflow_id,
        "employee_id":      employee_id,
        "candidate_name":   candidate_name,
        "candidate_email":  candidate_email,
        "role":             role,
        "department":       department,
        "joining_date":     joining_date,
        "stipend":          stipend,
        "acceptance_token": acceptance_token,
        "status":           status.value if isinstance(status, OfferStatus) else status,
        "sent_at":          now,
        "accepted_at":      None,
        "declined_at":      None,
        "created_at":       now,
        "updated_at":       now,
        "metadata":         metadata or {},
    }
