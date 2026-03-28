"""MCP-style message schemas for inter-agent communication."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum


class AgentType(str, Enum):
    """Agent types in the system."""
    ORCHESTRATOR = "orchestrator_agent"
    LIAISON = "liaison_agent"
    GUIDE = "guide_agent"
    PROVISIONING = "provisioning_agent"
    SCHEDULER = "scheduler_agent"


class MessageType(str, Enum):
    """Message types."""
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"


class WorkflowState(str, Enum):
    """Workflow states."""
    CREATED = "CREATED"
    INITIATED = "INITIATED"
    # Pre-joining offer flow
    OFFER_SENT = "OFFER_SENT"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_DECLINED = "OFFER_DECLINED"
    DOCUMENTS_REQUESTED = "DOCUMENTS_REQUESTED"
    DOCUMENTS_SUBMITTED = "DOCUMENTS_SUBMITTED"
    MANAGER_ASSIGNED = "MANAGER_ASSIGNED"
    # Provisioning
    PROVISIONING_PENDING = "PROVISIONING_PENDING"
    SCHEDULING_PENDING = "SCHEDULING_PENDING"
    CREDENTIALS_SENT = "CREDENTIALS_SENT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    ACTIVE = "ACTIVE"
    READY_FOR_DAY_1 = "READY_FOR_DAY_1"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskPayload(BaseModel):
    """Task payload for delegation."""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific data")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1-10)")
    retry_count: int = Field(default=0, description="Number of retries")


class MCPMessage(BaseModel):
    """MCP-style structured message envelope."""
    message_id: str = Field(..., description="Unique message identifier")
    workflow_id: str = Field(..., description="Workflow identifier")
    tenant_id: str = Field(..., description="Tenant/company identifier")
    from_agent: AgentType = Field(..., description="Source agent")
    to_agent: AgentType = Field(..., description="Destination agent")
    message_type: MessageType = Field(..., description="Type of message")
    task: Optional[TaskPayload] = Field(None, description="Task details if applicable")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional message data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = Field(None, description="For tracking related messages")


class DelegateTask(BaseModel):
    """Orchestrator output for task delegation."""
    action: Literal["delegate_task", "update_state", "complete_workflow", "retry_task", "escalate"]
    workflow_id: str
    tenant_id: str
    target_agent: Optional[AgentType] = None
    task: Optional[TaskPayload] = None
    new_state: Optional[WorkflowState] = None
    reason: str = Field(..., description="Explanation for action")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OnboardingInitiation(BaseModel):
    """Request to initiate onboarding workflow."""
    tenant_id: str = Field(..., description="Company/tenant identifier")
    employee_id: str = Field(..., description="New hire employee ID")
    employee_name: str = Field(..., description="New hire name")
    employee_email: str = Field(..., description="New hire email")
    role: str = Field(..., description="Job role/title")
    department: str = Field(..., description="Department")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    manager_id: Optional[str] = Field(None, description="Manager employee ID")
    manager_email: Optional[str] = Field(None, description="Manager email")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result from a delegated task."""
    task_id: str
    workflow_id: str
    tenant_id: str
    from_agent: AgentType
    status: Literal["success", "failure", "pending"]
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_possible: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
