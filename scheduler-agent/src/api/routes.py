"""REST API endpoints for Scheduler Agent.

Endpoints
---------
GET  /health          – Liveness / readiness probe
GET  /status          – Agent configuration and runtime stats
POST /execute-task    – Direct task execution (development / testing)
GET  /cache           – View idempotency cache (debugging)
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from src.agent.scheduler import scheduler_agent
from src.messaging.redis_client import redis_client
from src.schemas.mcp_message import AgentType, MCPMessage, MessageType, TaskPayload

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    agent: str
    redis_connected: bool
    version: str


class TaskRequest(BaseModel):
    """Direct task execution payload (bypasses Redis – for testing only)."""
    workflow_id: str
    tenant_id: str
    task: TaskPayload


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness / readiness probe."""
    redis_ok = redis_client.health_check()
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        agent="scheduler_agent",
        redis_connected=redis_ok,
        version="1.0.0",
    )


@router.get("/status")
async def get_status():
    """Return agent runtime status and configuration."""
    return {
        "agent": "scheduler_agent",
        "mode": "deterministic",
        "ai_enabled": False,
        "idempotency_enabled": True,
        "processed_tasks": len(scheduler_agent._processed_tasks),
        "supported_task_types": list(scheduler_agent.task_handlers.keys()),
        "n8n_endpoints": {
            "schedule_meeting": "/schedule-meeting",
            "reschedule_meeting": "/reschedule-meeting",
            "cancel_meeting": "/cancel-meeting",
        },
    }


@router.post("/execute-task")
async def execute_task(request: TaskRequest):
    """
    Execute a scheduling task directly without going through Redis.

    This endpoint is intended for development / integration testing.
    In production all tasks arrive via Redis Streams from Orchestrator.
    """
    try:
        message = MCPMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            workflow_id=request.workflow_id,
            tenant_id=request.tenant_id,
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=AgentType.SCHEDULER,
            message_type=MessageType.TASK_REQUEST,
            task=request.task,
        )

        result = await scheduler_agent.process_task(message)

        return {
            "action": "task_result",
            "workflow_id": result.workflow_id,
            "tenant_id": result.tenant_id,
            "task_id": result.task_id,
            "status": "success" if result.status == "success" else "failed",
            "result": result.result,
            "error": result.error,
            "retryable": result.retry_possible,
        }

    except Exception as exc:
        logger.error(f"Error executing task via API: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cache")
async def get_cache():
    """Return idempotency cache contents (task IDs only – no PII)."""
    return {
        "cached_tasks": len(scheduler_agent._processed_tasks),
        "task_keys": list(scheduler_agent._processed_tasks.keys()),
    }


@router.delete("/cache")
async def clear_cache():
    """Clear the in-memory idempotency cache (testing / debugging only)."""
    count = len(scheduler_agent._processed_tasks)
    scheduler_agent._processed_tasks.clear()
    logger.warning(f"Idempotency cache cleared ({count} entries removed)")
    return {"cleared": count}
