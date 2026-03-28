"""FastAPI application for Liaison Agent."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pathlib import Path
from typing import Optional
import uuid

from src.config.settings import settings
from src.schemas.liaison_message import (
    UserMessage, LiaisonResponse, ApprovalResponse,
    PolicyQueryRequest, TaskDelegationRequest
)
from src.schemas.mcp_message import AgentType, MessageType
from src.agent.liaison import liaison_agent, IntentType, LiaisonAction
from src.messaging.redis_client import redis_client

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Configure logging
logger.add(
    "logs/liaison.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Initialize FastAPI app
app = FastAPI(
    title="Liaison Agent",
    description="Conversational router and intent detection agent for AgenticHR",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting Liaison Agent")
    logger.info(f"Liaison Agent ready on port {settings.liaison_agent_url}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": "liaison_agent",
        "version": "1.0.0"
    }


@app.post("/message", response_model=LiaisonResponse)
async def process_user_message(
    user_msg: UserMessage,
    background_tasks: BackgroundTasks
):
    """
    Process incoming user message.
    
    This endpoint:
    1. Receives user message
    2. Classifies intent
    3. Routes to appropriate agent
    4. Returns response to user
    """
    try:
        logger.info(f"Received message from user {user_msg.user_id} (tenant: {user_msg.tenant_id})")
        
        # Process message through liaison agent
        routing_result = liaison_agent.process_message(
            user_message=user_msg.message,
            tenant_id=user_msg.tenant_id,
            workflow_id=user_msg.workflow_id,
            user_id=user_msg.user_id,
            metadata={
                "user_name": user_msg.user_name,
                "user_role": user_msg.user_role,
                **user_msg.metadata
            }
        )
        
        # Handle routing based on action
        action = routing_result.get("action")
        intent = routing_result.get("intent_type")
        
        # Route to appropriate agent in background
        if action == LiaisonAction.ROUTE_TO_GUIDE.value:
            background_tasks.add_task(
                _route_to_guide,
                routing_result,
                user_msg.user_id
            )
            response_text = "Let me check the policy information for you..."
            
        elif action == LiaisonAction.DELEGATE_TO_ORCHESTRATOR.value:
            background_tasks.add_task(
                _delegate_to_orchestrator,
                routing_result,
                user_msg.user_id
            )
            response_text = routing_result.get("user_response") or "I'll process your request and get back to you shortly."
            
        elif action == LiaisonAction.ASK_CLARIFICATION.value:
            response_text = routing_result.get("user_response") or "Could you provide more details?"
            
        else:  # acknowledge
            response_text = routing_result.get("user_response") or "Understood."
        
        # Create response
        response = LiaisonResponse(
            response_text=response_text,
            intent_type=intent,
            confidence_score=routing_result.get("confidence_score", 0.0),
            action_taken=action,
            workflow_id=routing_result.get("workflow_id"),
            metadata={
                "reason": routing_result.get("reason"),
                "payload": routing_result.get("payload", {})
            }
        )
        
        logger.info(f"Response sent to user {user_msg.user_id}: {action}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approval", response_model=LiaisonResponse)
async def process_approval_response(
    approval: ApprovalResponse,
    background_tasks: BackgroundTasks
):
    """
    Process user's approval/rejection response.
    
    This endpoint:
    1. Receives approval decision
    2. Formats structured response
    3. Sends to Orchestrator Agent
    """
    try:
        logger.info(f"Received approval response: {approval.approval_status} for workflow {approval.workflow_id}")
        
        # Create routing result for approval
        routing_result = {
            "action": LiaisonAction.DELEGATE_TO_ORCHESTRATOR.value,
            "workflow_id": approval.workflow_id,
            "tenant_id": approval.tenant_id,
            "intent_type": IntentType.APPROVAL_RESPONSE.value,
            "confidence_score": 1.0,
            "payload": {
                "original_message": f"Approval: {approval.approval_status}",
                "structured_data": {
                    "approval_status": approval.approval_status,
                    "approver_id": approval.user_id,
                    "approver_note": approval.approver_note,
                    "timestamp": approval.timestamp.isoformat()
                }
            },
            "reason": "Processing approval response"
        }
        
        # Send to Orchestrator
        background_tasks.add_task(
            _delegate_to_orchestrator,
            routing_result,
            approval.user_id
        )
        
        response_text = f"Your decision to {approval.approval_status} has been recorded. Thank you!"
        
        response = LiaisonResponse(
            response_text=response_text,
            intent_type=IntentType.APPROVAL_RESPONSE.value,
            confidence_score=1.0,
            action_taken=LiaisonAction.DELEGATE_TO_ORCHESTRATOR.value,
            workflow_id=approval.workflow_id,
            metadata={"approval_status": approval.approval_status}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guide-response")
async def receive_guide_response(
    guide_response: dict
):
    """
    Receive response from Guide Agent.
    
    This endpoint receives policy responses from the Guide Agent
    and can forward them back to the user.
    """
    try:
        tenant_id = guide_response.get("tenant_id")
        workflow_id = guide_response.get("workflow_id")
        response_text = guide_response.get("response", "")
        original_query = guide_response.get("query", "")
        
        logger.info(f"Received guide response for workflow {workflow_id}")
        
        # Process guide response
        result = liaison_agent.process_guide_response(
            guide_response=response_text,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            original_query=original_query
        )
        
        return {
            "status": "success",
            "response": result.get("user_response"),
            "workflow_id": workflow_id
        }
        
    except Exception as e:
        logger.error(f"Error processing guide response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approval-request")
async def receive_approval_request(
    approval_request: dict
):
    """
    Receive approval request from Orchestrator Agent.
    
    This endpoint receives approval requests and formats them
    for user presentation.
    """
    try:
        tenant_id = approval_request.get("tenant_id")
        workflow_id = approval_request.get("workflow_id")
        task_type = approval_request.get("task_type")
        details = approval_request.get("details", {})
        
        logger.info(f"Received approval request for workflow {workflow_id}")
        
        # Process approval request
        result = liaison_agent.process_approval_request(
            approval_data={"task_type": task_type, "details": details},
            tenant_id=tenant_id,
            workflow_id=workflow_id
        )
        
        return {
            "status": "success",
            "message": result.get("user_response"),
            "workflow_id": workflow_id,
            "requires_approval": True
        }
        
    except Exception as e:
        logger.error(f"Error processing approval request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversation/{tenant_id}/{workflow_id}")
async def clear_conversation(
    tenant_id: str,
    workflow_id: Optional[str] = None
):
    """Clear conversation history for a specific conversation."""
    try:
        liaison_agent.clear_conversation_history(tenant_id, workflow_id)
        return {
            "status": "success",
            "message": "Conversation history cleared"
        }
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions

async def _route_to_guide(routing_result: dict, user_id: str):
    """Route policy query to Guide Agent."""
    try:
        # Create MCP message
        mcp_message = liaison_agent.create_mcp_message(
            routing_result=routing_result,
            to_agent=AgentType.GUIDE,
            message_type=MessageType.QUERY
        )
        
        # Publish to Redis
        redis_client.publish_message(mcp_message)
        logger.info(f"Routed policy query to Guide Agent for workflow {routing_result.get('workflow_id')}")
        
    except Exception as e:
        logger.error(f"Error routing to guide: {e}")


async def _delegate_to_orchestrator(routing_result: dict, user_id: str):
    """Delegate task request to Orchestrator Agent."""
    try:
        # Create MCP message
        mcp_message = liaison_agent.create_mcp_message(
            routing_result=routing_result,
            to_agent=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_REQUEST
        )
        
        # Publish to Redis
        redis_client.publish_message(mcp_message)
        logger.info(f"Delegated task to Orchestrator for workflow {routing_result.get('workflow_id')}")
        
    except Exception as e:
        logger.error(f"Error delegating to orchestrator: {e}")


if __name__ == "__main__":
    import uvicorn
    
    # Extract port from liaison_agent_url
    port = 8002  # Default liaison agent port
    
    uvicorn.run(
        "src.api.liaison_main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.environment == "development",
        workers=1
    )
