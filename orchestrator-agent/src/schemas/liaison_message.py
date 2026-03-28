"""Liaison Agent specific message schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone


class UserMessage(BaseModel):
    """Incoming user message to Liaison Agent."""
    message: str = Field(..., description="User's message text")
    tenant_id: str = Field(..., description="Tenant/company identifier")
    user_id: str = Field(..., description="User identifier (employee_id or email)")
    workflow_id: Optional[str] = Field(None, description="Workflow ID if part of ongoing conversation")
    user_name: Optional[str] = Field(None, description="User's display name")
    user_role: Optional[str] = Field(None, description="User's role (employee, manager, hr)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LiaisonResponse(BaseModel):
    """Response from Liaison Agent to user."""
    response_text: str = Field(..., description="Response text to display to user")
    intent_type: str = Field(..., description="Classified intent type")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Intent classification confidence")
    action_taken: str = Field(..., description="Action taken by liaison agent")
    workflow_id: Optional[str] = Field(None, description="Workflow ID")
    requires_approval: bool = Field(default=False, description="Whether this requires user approval")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyQueryRequest(BaseModel):
    """Request to Guide Agent for policy query."""
    query: str = Field(..., description="Policy question")
    tenant_id: str = Field(..., description="Tenant identifier")
    workflow_id: str = Field(..., description="Workflow identifier")
    user_id: str = Field(..., description="User identifier")
    query_topic: Optional[str] = Field(None, description="Topic category")
    keywords: list[str] = Field(default_factory=list, description="Relevant keywords")


class TaskDelegationRequest(BaseModel):
    """Request to Orchestrator Agent for task delegation."""
    request_type: str = Field(..., description="Type of request (e.g., leave_application, meeting_schedule)")
    tenant_id: str = Field(..., description="Tenant identifier")
    workflow_id: str = Field(..., description="Workflow identifier")
    user_id: str = Field(..., description="User identifier requesting the task")
    structured_data: Dict[str, Any] = Field(..., description="Extracted structured data from conversation")
    original_message: str = Field(..., description="Original user message")
    urgency_level: Literal["low", "medium", "high"] = Field(default="medium", description="Task urgency")


class ApprovalResponse(BaseModel):
    """User's response to approval request."""
    workflow_id: str = Field(..., description="Workflow identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier (approver)")
    approval_status: Literal["approved", "rejected", "pending"] = Field(..., description="Approval decision")
    approver_note: Optional[str] = Field(None, description="Optional note from approver")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClarificationRequest(BaseModel):
    """Request for clarification from user."""
    workflow_id: Optional[str] = Field(None, description="Workflow identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    missing_fields: list[str] = Field(..., description="List of missing required fields")
    clarification_message: str = Field(..., description="Message requesting clarification")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current context")


class ConversationContext(BaseModel):
    """Conversation context for multi-turn dialogue."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    turn_count: int = Field(default=0, description="Number of conversation turns")
    last_intent: Optional[str] = Field(None, description="Last classified intent")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Data extracted across conversation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LiaisonRoutingDecision(BaseModel):
    """Internal routing decision structure."""
    action: Literal["route_to_guide", "delegate_to_orchestrator", "ask_clarification", "acknowledge"]
    workflow_id: Optional[str] = None
    tenant_id: str
    intent_type: Literal["POLICY_QUERY", "TASK_REQUEST", "APPROVAL_RESPONSE", "GENERAL_QUERY"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    payload: Dict[str, Any]
    reason: str
    user_response: Optional[str] = None
