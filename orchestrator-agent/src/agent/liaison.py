"""Core Liaison Agent logic using Groq LLM."""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, Optional, List
from loguru import logger
import json
import uuid
from datetime import datetime, timezone
from enum import Enum

from src.config.settings import settings
from src.schemas.mcp_message import (
    MCPMessage, AgentType, MessageType
)


class IntentType(str, Enum):
    """Intent classification types."""
    POLICY_QUERY = "POLICY_QUERY"
    TASK_REQUEST = "TASK_REQUEST"
    APPROVAL_RESPONSE = "APPROVAL_RESPONSE"
    GENERAL_QUERY = "GENERAL_QUERY"


class LiaisonAction(str, Enum):
    """Liaison agent actions."""
    ROUTE_TO_GUIDE = "route_to_guide"
    DELEGATE_TO_ORCHESTRATOR = "delegate_to_orchestrator"
    ASK_CLARIFICATION = "ask_clarification"
    ACKNOWLEDGE = "acknowledge"


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
        self.model = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )
        self.agent_type = AgentType.LIAISON
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        logger.info(f"Liaison Agent initialized with Groq model: {settings.groq_model}")
        
        self.system_prompt = """You are the Liaison Agent in a distributed multi-agent onboarding system called "AgenticHR".

You are NOT a generic chatbot.
You are a structured conversational router and intent detection agent.

PROJECT CONTEXT:
AgenticHR is a multi-agent onboarding orchestration system for freshers and interns.

There are 5 agents:
1. Orchestrator Agent (workflow planner)
2. Liaison Agent (you – conversation + routing)
3. Guide Agent (policy RAG – already implemented)
4. Provisioning Agent
5. Scheduler Agent

All agents communicate using structured MCP-style JSON messages via Redis Streams.

You NEVER execute external APIs.
You NEVER directly schedule meetings.
You NEVER create tickets.
You ONLY route and structure requests.

YOUR RESPONSIBILITIES:
1. Handle conversation with new hires and HR
2. Detect user intent
3. Classify messages into: POLICY_QUERY, TASK_REQUEST, APPROVAL_RESPONSE, GENERAL_QUERY
4. Route policy questions to Guide Agent
5. Send structured task requests to Orchestrator Agent
6. Ask clarification questions if required information is missing
7. Maintain conversational context
8. Never hallucinate company policies

INTENT CLASSIFICATION RULES:

If the user asks about:
- Leaves
- Company rules
- Holidays
- Benefits
- Working hours
- Internship policy
→ This is POLICY_QUERY. Route to Guide Agent.

If the user requests:
- Apply leave
- Schedule meeting
- Change joining date
- Request laptop
- Ask for ID card
- Submit documents
- Any action that requires execution
→ This is TASK_REQUEST. Send structured delegation request to Orchestrator.

If the user says:
- "Yes"
- "Approve"
- "Reject"
- "I confirm"
- "Proceed"
→ This is APPROVAL_RESPONSE. Forward structured response to Orchestrator.

Otherwise:
→ This is GENERAL_QUERY. Provide conversational response or ask clarification.

COMMUNICATION FORMAT (STRICT):
You must output ONLY valid JSON.

Format:
{
  "action": "route_to_guide" | "delegate_to_orchestrator" | "ask_clarification" | "acknowledge",
  "workflow_id": "string or null",
  "tenant_id": "string",
  "intent_type": "POLICY_QUERY | TASK_REQUEST | APPROVAL_RESPONSE | GENERAL_QUERY",
  "confidence_score": 0.0-1.0,
  "payload": {
      "original_message": "user message",
      "structured_data": { ... extracted fields ... }
  },
  "reason": "brief reasoning",
  "user_response": "conversational response text if applicable"
}

FIELD EXTRACTION RULES:

For TASK_REQUEST:
Extract:
- request_type (e.g., "leave_application", "meeting_schedule", "laptop_request")
- dates (if any, in YYYY-MM-DD format)
- duration (if any)
- reason (if mentioned)
- employee_name (if provided)
- manager_email (if relevant)
- urgency_level (low, medium, high)

If missing required fields:
- Set action to "ask_clarification"
- Include specific missing fields in user_response
- Do NOT guess

For POLICY_QUERY:
Include:
- query_topic (e.g., "leave_policy", "working_hours", "benefits")
- keywords (list of relevant terms)
- full_query (original user message)

For APPROVAL_RESPONSE:
Extract:
- approval_status ("approved" | "rejected" | "pending")
- approver_note (if any)
- workflow_id (must be from context)

GUIDE AGENT INTEGRATION:
When routing to Guide Agent:
- Include tenant_id
- Include full user query
- Do NOT modify policy content
- Do NOT fabricate answers

You are NOT allowed to answer policy questions yourself.

CONVERSATION MEMORY:
- Maintain context of previous conversation
- Use workflow_id to track ongoing conversation
- Avoid asking repeated questions
- Remember previously provided dates or reasons

SECURITY RULES:
- Never expose internal system architecture
- Never expose other agents' logic
- Never leak tenant data
- Never mix tenant information
- Never fabricate approvals

BEHAVIOR CONSTRAINTS:
- Be concise internally
- Think step-by-step internally
- Do not expose chain-of-thought
- Output only final structured JSON

NEVER output plain text.
NEVER output markdown.
NEVER explain outside JSON.
Output ONLY valid JSON."""

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
            history = self.conversation_history.get(conv_key, [])
            
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
        """Update conversation history."""
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
    
    def _create_error_response(
        self,
        tenant_id: str,
        error_message: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create error response."""
        return {
            "action": LiaisonAction.ASK_CLARIFICATION.value,
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "intent_type": IntentType.GENERAL_QUERY.value,
            "confidence_score": 0.0,
            "payload": {
                "original_message": "",
                "structured_data": {},
                "error": error_message
            },
            "reason": f"Error processing request: {error_message}",
            "user_response": "I apologize, but I encountered an error processing your request. Could you please rephrase or try again?"
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
            logger.info(f"Cleared conversation history for {conv_key}")


# Global instance
liaison_agent = LiaisonAgent()
