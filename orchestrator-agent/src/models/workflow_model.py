"""MongoDB document models for workflow and task storage."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow status."""
    CREATED = "CREATED"
    INITIATED = "INITIATED"
    PROVISIONING_PENDING = "PROVISIONING_PENDING"
    SCHEDULING_PENDING = "SCHEDULING_PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


def workflow_to_dict(
    workflow_id: str,
    tenant_id: str,
    employee_id: str,
    employee_name: str,
    employee_email: str,
    role: str,
    department: str,
    start_date: str,
    manager_id: Optional[str] = None,
    manager_email: Optional[str] = None,
    status: WorkflowStatus = WorkflowStatus.CREATED,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Convert workflow data to MongoDB document."""
    return {
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "employee_email": employee_email,
        "role": role,
        "department": department,
        "start_date": start_date,
        "manager_id": manager_id,
        "manager_email": manager_email,
        "status": status.value if isinstance(status, WorkflowStatus) else status,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completed_at": None,
        "metadata": metadata or {}
    }


def task_to_dict(
    task_id: str,
    workflow_id: str,
    tenant_id: str,
    task_type: str,
    assigned_agent: str,
    payload: Dict[str, Any] = None,
    status: TaskStatus = TaskStatus.PENDING,
    retry_count: int = 0,
    max_retries: int = 2
) -> Dict[str, Any]:
    """Convert task data to MongoDB document."""
    return {
        "task_id": task_id,
        "workflow_id": workflow_id,
        "tenant_id": tenant_id,
        "task_type": task_type,
        "assigned_agent": assigned_agent,
        "status": status.value if isinstance(status, TaskStatus) else status,
        "payload": payload or {},
        "result": None,
        "error": None,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completed_at": None
    }