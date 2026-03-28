"""Core Liaison Agent logic using Groq LLM."""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, Optional, List
from loguru import logger
import json
import uuid
import asyncio
from datetime import datetime, timezone
from enum import Enum

from src.config.settings import settings
from src.schemas.mcp_message import (
    MCPMessage, AgentType, MessageType
)


class IntentType(str, Enum):
    """Intent classification types."""
    POLICY_QUERY       = "POLICY_QUERY"
    TASK_REQUEST       = "TASK_REQUEST"
    APPROVAL_RESPONSE  = "APPROVAL_RESPONSE"
    GENERAL_QUERY      = "GENERAL_QUERY"
    LEAVE_REQUEST      = "LEAVE_REQUEST"
    ONBOARDING_PROGRESS= "ONBOARDING_PROGRESS"
    HR_ACTION          = "HR_ACTION"


class LiaisonAction(str, Enum):
    """Liaison agent actions."""
    ROUTE_TO_GUIDE         = "route_to_guide"
    DELEGATE_TO_ORCHESTRATOR = "delegate_to_orchestrator"
    ASK_CLARIFICATION      = "ask_clarification"
    ACKNOWLEDGE            = "acknowledge"
    ROUTE_LEAVE_REQUEST    = "route_leave_request"
    ROUTE_ONBOARDING       = "route_onboarding_journey"
    ROUTE_HR_ACTION        = "route_hr_action"


class LiaisonAgent:
    """
    Liaison Agent - Conversational router and intent detection.
    
    This agent:
    - Handles conversations with new hires and HR
    - Detects user intent
    - Classifies messages into intent types
    - Routes policy queries to Guide Agent
    - Sends structured task requests to Orchestrator
    - Asks clarification questions when needed
    - Maintains conversational context
    - Never hallucinates company policies
    """
    
    def __init__(self):
        """Initialize Liaison Agent."""
        # Validate API key before configuring
        self.model = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )
        self.agent_type = AgentType.LIAISON
        # In-memory cache; Redis is the source of truth (see _load_history/_save_history)
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        logger.info(f"Liaison Agent initialized with Groq model: {settings.groq_model}")
        
        self.system_prompt = """You are the Liaison Agent in AgenticHR — an AI-powered Employee Onboarding and Assistance Platform.

You are a structured conversational router and intent detection agent — NOT a generic chatbot.

AGENTS IN THE SYSTEM:
1. Orchestrator Agent (workflow planner + leave request manager)
2. Liaison Agent (YOU – conversation + routing)
3. Guide Agent (RAG policy assistant + leave approval executor + onboarding companion)
4. Provisioning Agent (Employee Setup Agent – creates records, credentials, checklists)
5. Scheduler Agent (Google Calendar + Meet automation)

RESPONSIBILITIES:
1. Detect user intent from natural language
2. Classify into EXACTLY one of the 7 intent types below
3. Route to the correct agent or endpoint
4. Ask clarification only when truly required
5. Maintain conversational context
6. Never hallucinate policies or approvals

INTENT TYPES AND ROUTING:

1. POLICY_QUERY → route_to_guide
   Triggered when user asks (read-only questions):
   - Leave policy, sick leave, earned leave rules
   - Company rules, working hours, code of conduct
   - Benefits, insurance, reimbursements
   - Holidays, observances

2. LEAVE_REQUEST → route_leave_request
   Triggered when user wants to TAKE or APPLY for leave:
   - "I need leave", "apply leave", "request leave off"
   - "I want to take sick leave", "can I take 2 days off"
   Route to Guide Agent (it executes the full approval workflow autonomously)

3. ONBOARDING_PROGRESS → route_onboarding_journey
   Triggered when employee asks about their onboarding:
   - "What are my onboarding tasks?", "what should I do next?"
   - "Show my onboarding progress", "what is my checklist?"
   Route to Guide Agent (it fetches journey + suggests next steps)

4. TASK_REQUEST → delegate_to_orchestrator
   Triggered when user requests execution of a task:
   - Schedule meeting, set up access, request equipment
   - Submit documents, change joining date
   - Any action beyond leave requests

5. APPROVAL_RESPONSE → delegate_to_orchestrator
   Triggered when user says yes/no/approve/reject to a pending request

6. HR_ACTION → route_hr_action
   Triggered when HR role user performs management actions:
   - "Show pending leave requests", "approve leave for John"
   - "View onboarding progress of interns"
   - "Upload company policies"
   - "Trigger onboarding for new hire"
   - "Schedule a meeting/meet with [intern] on [date] at [time]"
   - "Set up a call with [person] on [date]"

7. GENERAL_QUERY → route_to_guide
   Everything else — greeting, small talk, general questions, conversational queries
   ALWAYS route to Guide Agent so it can provide a helpful, contextual response
   NEVER just acknowledge without routing — every message deserves a thoughtful response

OUTPUT FORMAT (STRICT — valid JSON only, NO markdown, NO extra text):
{
  "action": "route_to_guide" | "route_leave_request" | "route_onboarding_journey" | "delegate_to_orchestrator" | "ask_clarification" | "acknowledge" | "route_hr_action",
  "workflow_id": "string or null",
  "tenant_id": "string",
  "intent_type": "POLICY_QUERY" | "LEAVE_REQUEST" | "ONBOARDING_PROGRESS" | "TASK_REQUEST" | "APPROVAL_RESPONSE" | "HR_ACTION" | "GENERAL_QUERY",
  "confidence_score": 0.0-1.0,
  "payload": {
    "original_message": "full user message",
    "structured_data": {
      ... context-specific extracted fields ...
    }
  },
  "reason": "one-line reasoning",
  "user_response": "brief formal acknowledgement ONLY — never say 'on the way', 'please wait', or any delivery-app style placeholder. For guide-routed intents write only: 'Retrieving the information now.'"
}

EXTRACTION RULES:

For LEAVE_REQUEST, extract into structured_data:
  - leave_type: "casual" | "sick" | "earned" | "unpaid" (infer or ask)
  - start_date: YYYY-MM-DD (ask if not provided)
  - end_date: YYYY-MM-DD (same as start for single day)
  - num_days: number (ask if unclear)
  - reason: string (optional)
  - employee_id: from user_id
  - employee_email: from user metadata

For TASK_REQUEST, extract:
  - request_type: "meeting_schedule" | "equipment_request" | "document_submission" | etc
  - dates, participants, urgency_level

For HR_ACTION, extract:
  - hr_action_type: "view_leave_requests" | "approve_leave" | "upload_policy" | "view_onboarding" | "schedule_meeting" | etc
  - target_employee_id (if applicable)
  For hr_action_type = "schedule_meeting", also extract:
    - intern_email: email address of the intern/employee to meet with
    - intern_name: name of intern if mentioned (optional)
    - date: YYYY-MM-DD (extract from "March 15", "tomorrow", "next Monday", etc.)
    - time: HH:MM in 24h format (extract from "2pm", "14:00", "morning" → "10:00", etc.)
    - duration_mins: duration in minutes (default 60 if not specified)
    - title: meeting title from context (default "HR Meeting")

For ONBOARDING_PROGRESS:
  - employee_id: from user_id

ASK CLARIFICATION only when ABSOLUTELY necessary:
- Leave dates are completely missing AND user explicitly wants to apply for leave
- User's message is incomprehensible (random characters, no discernible meaning)

IMPORTANT ROUTING RULES:
- For greetings (hi, hello, hey) → route_to_guide (Guide will respond warmly)
- For simple questions → route_to_guide (Guide will answer)
- For policy questions → route_to_guide
- CRITICAL: NEVER use ask_clarification for greeting messages, simple questions, or any message with a clear meaning
- CRITICAL: NEVER tell the user to "rephrase" — always try to answer or route
- CRITICAL: NEVER return ask_clarification just because dates/details are missing for a general query
- When in doubt about anything except leave dates → route_to_guide immediately
- Every message must get a real response, not a deflection

SECURITY:
- NEVER mix data across tenants
- NEVER hallucinate policy answers
- NEVER expose internal agent architecture to users

OUTPUT ONLY VALID JSON — NO exceptions."""

    def process_message(
        self,
        user_message: str,
        tenant_id: str,
        workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming user message and determine routing.
        
        Args:
            user_message: User's message
            tenant_id: Tenant/company identifier
            workflow_id: Workflow ID if part of ongoing conversation
            user_id: User identifier
            metadata: Additional metadata
            
        Returns:
            Structured routing decision
        """
        try:
            # Generate conversation key
            conv_key = f"{tenant_id}_{workflow_id or user_id or 'default'}"
            
            # Get conversation history
            history = self._load_history(conv_key)
            
            # Build context
            context = self._build_context(
                user_message=user_message,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                history=history,
                metadata=metadata
            )
            
            # Get LLM response
            logger.info(f"Processing message for tenant {tenant_id}: {user_message[:50]}...")
            
            response = self.model.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"\nCONTEXT:\n{json.dumps(context, indent=2)}"
                    f"\n\nUSER MESSAGE:\n{user_message}"
                    "\n\nProvide ONLY the JSON response. No markdown, no explanations."
                )),
            ])

            # Parse response
            result = self._parse_llm_response(response.content)
            
            # Update conversation history
            self._update_history(conv_key, user_message, result)
            
            logger.info(f"Intent classified: {result.get('intent_type')} with confidence {result.get('confidence_score')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._create_error_response(tenant_id, str(e), workflow_id)
    
    def process_guide_response(
        self,
        guide_response: str,
        tenant_id: str,
        workflow_id: str,
        original_query: str
    ) -> Dict[str, Any]:
        """
        Process response from Guide Agent and format for user.
        
        Args:
            guide_response: Response from Guide Agent
            tenant_id: Tenant identifier
            workflow_id: Workflow identifier
            original_query: Original user query
            
        Returns:
            Formatted response
        """
        try:
            result = {
                "action": "acknowledge",
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "intent_type": IntentType.POLICY_QUERY.value,
                "confidence_score": 1.0,
                "payload": {
                    "original_message": original_query,
                    "guide_response": guide_response,
                    "structured_data": {}
                },
                "reason": "Returning policy response from Guide Agent",
                "user_response": guide_response
            }
            
            # Update conversation history
            conv_key = f"{tenant_id}_{workflow_id}"
            self._update_history(conv_key, original_query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing guide response: {e}")
            return self._create_error_response(tenant_id, str(e), workflow_id)
    
    def process_approval_request(
        self,
        approval_data: Dict[str, Any],
        tenant_id: str,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Format approval request for user.
        
        Args:
            approval_data: Approval request data from Orchestrator
            tenant_id: Tenant identifier
            workflow_id: Workflow identifier
            
        Returns:
            Formatted approval request
        """
        try:
            # Extract approval details
            task_type = approval_data.get("task_type", "Unknown Task")
            details = approval_data.get("details", {})
            
            # Format user-friendly message
            user_message = self._format_approval_message(task_type, details)
            
            result = {
                "action": "ask_clarification",
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "intent_type": IntentType.APPROVAL_RESPONSE.value,
                "confidence_score": 1.0,
                "payload": {
                    "original_message": "Approval request",
                    "structured_data": approval_data
                },
                "reason": "Requesting user approval",
                "user_response": user_message
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing approval request: {e}")
            return self._create_error_response(tenant_id, str(e), workflow_id)
    
    def _load_history(self, conv_key: str) -> List[Dict[str, str]]:
        """Load conversation history from Redis (fallback to in-memory cache)."""
        try:
            from src.messaging.redis_client import redis_client as rc
            raw = rc.redis_client.hget("conv_history", conv_key)
            if raw:
                history = json.loads(raw)
                self.conversation_history[conv_key] = history
                return history
        except Exception as e:
            logger.warning(f"Could not load history from Redis for {conv_key}: {e}")
        return self.conversation_history.get(conv_key, [])

    def _save_history(self, conv_key: str, history: List[Dict[str, str]]) -> None:
        """Persist conversation history to Redis."""
        try:
            from src.messaging.redis_client import redis_client as rc
            rc.redis_client.hset("conv_history", conv_key, json.dumps(history[-20:]))
        except Exception as e:
            logger.warning(f"Could not save history to Redis for {conv_key}: {e}")

    def _build_context(
        self,
        user_message: str,
        tenant_id: str,
        workflow_id: Optional[str],
        history: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build context for LLM."""
        context = {
            "tenant_id": tenant_id,
            "workflow_id": workflow_id,
            "conversation_history": history[-5:] if history else [],  # Last 5 messages
            "metadata": metadata or {}
        }
        return context
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            result = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ["action", "tenant_id", "intent_type", "confidence_score", "payload", "reason"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate action
            valid_actions = [e.value for e in LiaisonAction]
            if result["action"] not in valid_actions:
                raise ValueError(f"Invalid action: {result['action']}")
            
            # Validate intent type
            valid_intents = [e.value for e in IntentType]
            if result["intent_type"] not in valid_intents:
                raise ValueError(f"Invalid intent type: {result['intent_type']}")
            
            # Validate confidence score
            if not (0.0 <= result["confidence_score"] <= 1.0):
                raise ValueError("confidence_score must be between 0.0 and 1.0")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {response_text}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            raise
    
    def _update_history(
        self,
        conv_key: str,
        user_message: str,
        result: Dict[str, Any]
    ) -> None:
        """Update conversation history in memory and Redis."""
        if conv_key not in self.conversation_history:
            self.conversation_history[conv_key] = []
        
        self.conversation_history[conv_key].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_message": user_message,
            "intent": result.get("intent_type"),
            "action": result.get("action"),
            "response": result.get("user_response", "")
        })
        
        # Keep only last 20 messages
        if len(self.conversation_history[conv_key]) > 20:
            self.conversation_history[conv_key] = self.conversation_history[conv_key][-20:]

        # Persist to Redis
        self._save_history(conv_key, self.conversation_history[conv_key])
    
    def _create_error_response(
        self,
        tenant_id: str,
        error_message: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create error response."""
        return {
            "action": LiaisonAction.ROUTE_TO_GUIDE.value,
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "intent_type": IntentType.GENERAL_QUERY.value,
            "confidence_score": 0.5,
            "payload": {
                "original_message": "",
                "structured_data": {},
                "error": error_message
            },
            "reason": f"Error processing request, routing to guide: {error_message}",
            "user_response": "Let me help you with that."
        }
    
    def _format_approval_message(
        self,
        task_type: str,
        details: Dict[str, Any]
    ) -> str:
        """Format approval request message for user."""
        messages = {
            "leave_application": f"Leave application request:\n- From: {details.get('start_date')}\n- To: {details.get('end_date')}\n- Reason: {details.get('reason', 'Not specified')}\n\nDo you approve this request? (Reply with 'approve' or 'reject')",
            "meeting_schedule": f"Meeting schedule request:\n- Date: {details.get('date')}\n- Time: {details.get('time')}\n- Attendees: {', '.join(details.get('attendees', []))}\n\nDo you approve? (Reply with 'approve' or 'reject')",
            "default": f"Approval required for {task_type}.\n\nDetails: {json.dumps(details, indent=2)}\n\nDo you approve? (Reply with 'approve' or 'reject')"
        }
        
        return messages.get(task_type, messages["default"])
    
    def create_mcp_message(
        self,
        routing_result: Dict[str, Any],
        to_agent: AgentType,
        message_type: MessageType = MessageType.QUERY
    ) -> MCPMessage:
        """
        Create MCP message from routing result.
        
        Args:
            routing_result: Routing decision from process_message
            to_agent: Target agent
            message_type: Type of message
            
        Returns:
            MCP message
        """
        message_id = f"MSG_{uuid.uuid4().hex[:12]}"
        
        return MCPMessage(
            message_id=message_id,
            workflow_id=routing_result.get("workflow_id") or f"WF_{uuid.uuid4().hex[:8]}",
            tenant_id=routing_result["tenant_id"],
            from_agent=self.agent_type,
            to_agent=to_agent,
            message_type=message_type,
            data=routing_result["payload"],
            metadata={
                "intent_type": routing_result["intent_type"],
                "confidence_score": routing_result["confidence_score"],
                "action": routing_result["action"]
            }
        )
    
    def clear_conversation_history(self, tenant_id: str, workflow_id: Optional[str] = None) -> None:
        """Clear conversation history for a specific conversation."""
        conv_key = f"{tenant_id}_{workflow_id or 'default'}"
        if conv_key in self.conversation_history:
            del self.conversation_history[conv_key]
        try:
            from src.messaging.redis_client import redis_client as rc
            rc.redis_client.hdel("conv_history", conv_key)
        except Exception as e:
            logger.warning(f"Could not clear Redis history for {conv_key}: {e}")
        logger.info(f"Cleared conversation history for {conv_key}")

    def handle_workflow_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow completion notification from Orchestrator."""
        workflow_id = payload.get("workflow_id", "")
        tenant_id = payload.get("tenant_id", "unknown")
        status = payload.get("status", "COMPLETED")
        employee_name = payload.get("employee_name", "")
        summary = payload.get("summary", {})

        if status == "COMPLETED":
            user_msg = (
                f"Great news{', ' + employee_name if employee_name else ''}! "
                f"Your onboarding workflow has been completed successfully. "
                f"All {summary.get('total_tasks', 0)} tasks are done."
            )
        else:
            user_msg = (
                f"Your onboarding workflow ({workflow_id}) encountered some issues. "
                f"Please contact your HR contact for assistance."
            )

        # Store so /pending-response polling can pick it up
        conv_key = f"{tenant_id}_{workflow_id}"
        history = self._load_history(conv_key)
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_message": f"[SYSTEM] workflow {status}",
            "intent": "WORKFLOW_COMPLETE",
            "action": "acknowledge",
            "response": user_msg
        })
        self._save_history(conv_key, history)
        self.conversation_history[conv_key] = history

        logger.info(f"Workflow {workflow_id} completion handled for tenant {tenant_id}")
        return {"workflow_id": workflow_id, "status": status, "user_message": user_msg}

    def run_listener_thread(self, stop_event: "threading.Event") -> None:
        """
        Synchronous Redis listener that runs in a dedicated daemon thread.
        Completely isolated from asyncio — never blocks the event loop.
        """
        import threading
        import time as _time
        from src.messaging.redis_client import redis_client as rc
        logger.info("Liaison Agent Redis listener thread running")
        while not stop_event.is_set():
            try:
                messages = rc.read_messages("liaison_agent", count=5, block=500)
                for msg_id, message in messages:
                    try:
                        msg_data = message.data if hasattr(message, "data") else {}
                        if message.message_type.value == "WORKFLOW_COMPLETE":
                            self.handle_workflow_completion(msg_data)
                        else:
                            logger.debug(f"Liaison received unhandled type: {message.message_type}")
                        rc.acknowledge_message(
                            "agent_stream:liaison_agent",
                            "liaison_agent_group",
                            msg_id
                        )
                    except Exception as msg_err:
                        logger.error(f"Liaison listener msg error: {msg_err}")
            except Exception as e:
                logger.error(f"Liaison listener loop error: {e}")
                _time.sleep(1)
        logger.info("Liaison Agent Redis listener thread stopped")


# Global instance
liaison_agent = LiaisonAgent()
