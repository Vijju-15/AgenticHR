"""MongoDB document models for candidate documents (ID proof, certificates, etc.)."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class DocType(str, Enum):
    GOVT_ID     = "govt_id"
    PHOTO       = "photo"
    CERTIFICATE = "certificate"
    OTHER       = "other"


class DocStatus(str, Enum):
    UPLOADED   = "uploaded"
    VERIFIED   = "verified"
    REJECTED   = "rejected"


def candidate_document_to_dict(
    doc_id: str,
    tenant_id: str,
    workflow_id: str,
    employee_id: str,
    doc_type: str,
    original_filename: str,
    storage_path: str,
    file_size_bytes: int = 0,
    status: DocStatus = DocStatus.UPLOADED,
    verified_by: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert document upload data to a MongoDB document."""
    now = datetime.now(timezone.utc)
    return {
        "doc_id":            doc_id,
        "tenant_id":         tenant_id,
        "workflow_id":       workflow_id,
        "employee_id":       employee_id,
        "doc_type":          doc_type,
        "original_filename": original_filename,
        "storage_path":      storage_path,
        "file_size_bytes":   file_size_bytes,
        "status":            status.value if isinstance(status, DocStatus) else status,
        "verified_by":       verified_by,
        "uploaded_at":       now,
        "updated_at":        now,
        "metadata":          metadata or {},
    }
