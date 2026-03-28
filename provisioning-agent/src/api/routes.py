"""REST API endpoints for Provisioning Agent."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from loguru import logger

from src.agent.provisioning import provisioning_agent
from src.messaging.redis_client import redis_client
from src.schemas.mcp_message import MCPMessage, TaskPayload

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    agent: str
    redis_connected: bool
    version: str


class TaskRequest(BaseModel):
    """Direct task execution request (for testing)."""
    workflow_id: str
    tenant_id: str
    task: TaskPayload


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    redis_ok = redis_client.health_check()
    
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        agent="provisioning_agent",
        redis_connected=redis_ok,
        version="1.0.0"
    )


@router.get("/status")
async def get_status():
    """Get agent status."""
    return {
        "agent": "provisioning_agent",
        "mode": "deterministic",
        "ai_enabled": False,
        "idempotency_enabled": True,
        "processed_tasks": len(provisioning_agent._processed_tasks),
        "supported_task_types": list(provisioning_agent.task_handlers.keys())
    }


@router.post("/execute-task")
async def execute_task(request: TaskRequest):
    """
    Execute task directly (for testing).
    
    In production, tasks come via Redis streams.
    """
    try:
        from src.schemas.mcp_message import AgentType, MessageType
        import uuid
        
        # Create MCP message
        message = MCPMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            workflow_id=request.workflow_id,
            tenant_id=request.tenant_id,
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=AgentType.PROVISIONING,
            message_type=MessageType.TASK_REQUEST,
            task=request.task
        )
        
        # Process task
        result = await provisioning_agent.process_task(message)
        
        return {
            "task_id": result.task_id,
            "status": result.status,
            "result": result.result,
            "error": result.error,
            "retry_possible": result.retry_possible
        }
        
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache")
async def get_cache():
    """Get cached task results (for debugging)."""
    return {
        "cached_tasks": len(provisioning_agent._processed_tasks),
        "tasks": list(provisioning_agent._processed_tasks.keys())
    }


@router.delete("/cache")
async def clear_cache():
    """Clear task cache."""
    provisioning_agent._processed_tasks.clear()
    return {"message": "Cache cleared"}
