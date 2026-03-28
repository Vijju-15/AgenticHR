"""Workflow data models."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow status enumeration."""
    CREATED = "CREATED"
    INITIATED = "INITIATED"
    PROVISIONING_PENDING = "PROVISIONING_PENDING"
    SCHEDULING_PENDING = "SCHEDULING_PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class Workflow(BaseModel):
    """Workflow model."""
    workflow_id: str
    tenant_id: str
    employee_id: str
    employee_name: str
    employee_email: str
    role: str
    department: str
    start_date: str
    manager_id: Optional[str] = None
    manager_email: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    completed_at: Optional[datetime] = None
    tasks: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class WorkflowTask(BaseModel):
    """Individual task within a workflow."""
    task_id: str
    workflow_id: str
    tenant_id: str
    task_type: str
    assigned_agent: str
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    completed_at: Optional[datetime] = None
