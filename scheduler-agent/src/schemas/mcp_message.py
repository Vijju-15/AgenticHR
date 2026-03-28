"""MCP-style message schemas for inter-agent communication."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
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


class MeetingPayload(BaseModel):
    """Validated meeting payload for scheduler tasks."""
    meeting_title: str
    description: Optional[str] = ""
    start_datetime: str
    end_datetime: str
    timezone: str
    organizer_email: str
    participants: List[str]
    meeting_type: Optional[str] = "induction"
    # Required for reschedule / cancel
    event_id: Optional[str] = None


class SchedulerTaskResult(BaseModel):
    """Scheduler-specific task result matching strict output format."""
    action: Literal["task_result"] = "task_result"
    workflow_id: str
    tenant_id: str
    task_id: str
    status: Literal["success", "failed"]
    result: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Contains: event_id, meet_link, start_datetime, end_datetime, "
            "calendar_url, details{meeting_title, participants}"
        )
    )
    error: Optional[str] = None
    retryable: bool = True
