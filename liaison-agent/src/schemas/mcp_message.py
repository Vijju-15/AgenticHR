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
