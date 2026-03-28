"""FastAPI application for Liaison Agent."""

import asyncio
import threading
import time
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pathlib import Path
from typing import Optional
import httpx

from src.config.settings import settings
from src.schemas.liaison_message import (
    UserMessage, LiaisonResponse, ApprovalResponse,
    PolicyQueryRequest, TaskDelegationRequest
)
from src.schemas.mcp_message import AgentType, MessageType
from src.agent.liaison import liaison_agent, IntentType, LiaisonAction
from src.messaging.redis_client import redis_client


_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _is_placeholder_date(value: Optional[str]) -> bool:
    text = (value or "").strip().lower()
    return text in {"", "today", "tomorrow", "now", "asap", "not specified", "n/a"}


def _extract_dates_from_text(text: str) -> list[datetime]:
    """Extract month-name dates like '22nd march 2026' from free text."""
    if not text:
        return []

    pattern = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s*(\d{4})?", re.IGNORECASE)
    now_year = datetime.now().year
    out: list[datetime] = []

    for m in pattern.finditer(text):
        day_raw, month_raw, year_raw = m.groups()
        month_key = month_raw.strip().lower()
        month = _MONTHS.get(month_key)
        if not month:
            continue
        day = int(day_raw)
        year = int(year_raw) if year_raw else now_year
        try:
            out.append(datetime(year=year, month=month, day=day))
        except ValueError:
            continue

    return out


def _summarize_recent_user_context(history: list[dict], max_items: int = 4) -> str:
    user_msgs = [h.get("user_message", "") for h in history if h.get("user_message") and not str(h.get("user_message", "")).startswith("[SYSTEM]")]
    if not user_msgs:
        return ""
    recent = user_msgs[-max_items:]
    summary = " | ".join(msg.strip() for msg in recent if msg.strip())
    return summary[:420]

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

_START_TIME = time.time()
_listener_thread: Optional[threading.Thread] = None
_listener_stop = threading.Event()


# Initialize FastAPI app (no lifespan — use on_event like orchestrator)
app = FastAPI(
    title="Liaison Agent",
    description="Conversational router and intent detection agent for AgenticHR",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Start the Redis stream listener in a daemon thread on startup."""
    global _listener_thread, _listener_stop
    logger.info("Starting Liaison Agent")
    logger.info(f"Liaison Agent ready on port {settings.api_port}")
    if not settings.groq_api_key or settings.groq_api_key == "":
        logger.warning("WARNING: GROQ_API_KEY is not set!")
    # Reset stop flag and launch daemon thread — completely isolated from asyncio
    _listener_stop.clear()
    _listener_thread = threading.Thread(
        target=liaison_agent.run_listener_thread,
        args=(_listener_stop,),
        daemon=True,
        name="liaison-redis-listener"
    )
    _listener_thread.start()
    logger.info("✅ Liaison Agent Redis listener thread started")


@app.on_event("shutdown")
async def shutdown_event():
    """Signal the listener thread to stop."""
    logger.info("👋 Liaison Agent shutting down")
    _listener_stop.set()
    if _listener_thread and _listener_thread.is_alive():
        _listener_thread.join(timeout=3)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API-key guard. Skipped when AGENTHR_API_KEY is not configured."""
    skip_prefixes = ("/health", "/metrics", "/docs", "/openapi.json", "/")
    if settings.api_key and not any(request.url.path.startswith(p) for p in skip_prefixes):
        key = request.headers.get("X-API-Key", "")
        if key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": "liaison_agent",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def get_metrics():
    """Runtime metrics for the Liaison Agent."""
    return {
        "agent": "liaison_agent",
        "uptime_seconds": int(time.time() - _START_TIME),
        "redis_connected": redis_client.health_check(),
        "conversation_sessions": len(liaison_agent.conversation_history),
        "stream_info": redis_client.get_stream_info("liaison_agent")
    }


@app.post("/workflow-complete")
async def workflow_complete(payload: dict):
    """
    Receive workflow completion/failure notification from Orchestrator.
    Stores result in conversation history so the new hire can be informed.
    """
    try:
        result = liaison_agent.handle_workflow_completion(payload)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Error handling workflow completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        # ── Guide Agent routes — called INLINE so the real answer is returned ──
        # Also route GENERAL_QUERY to guide for meaningful responses
        if action in (
            LiaisonAction.ROUTE_TO_GUIDE.value,
            LiaisonAction.ROUTE_LEAVE_REQUEST.value,
            LiaisonAction.ROUTE_ONBOARDING.value,
        ) or intent == IntentType.GENERAL_QUERY.value:
            try:
                response_text = await _call_guide_inline(routing_result, user_msg.user_id)
            except Exception as guide_err:
                logger.warning(f"Guide call failed, falling back to ack: {guide_err}")
                response_text = "The HR knowledge base is temporarily unavailable. Please try your question again in a moment."

        # ── HR action route (direct async call to orchestrator REST) ──────
        elif action == LiaisonAction.ROUTE_HR_ACTION.value:
            try:
                response_text = await _call_hr_action_inline(routing_result, user_msg.user_id)
            except Exception as hr_err:
                logger.warning(f"HR action failed inline: {hr_err}")
                response_text = routing_result.get("user_response") or "Processing your HR request…"

        # ── Orchestrator delegation ───────────────────────────────────────
        elif action == LiaisonAction.DELEGATE_TO_ORCHESTRATOR.value:
            background_tasks.add_task(
                _delegate_to_orchestrator,
                routing_result,
                user_msg.user_id
            )
            response_text = routing_result.get("user_response") or "I'll process your request and get back to you shortly."

        elif action == LiaisonAction.ASK_CLARIFICATION.value:
            # Always try guide agent first — never just say "please rephrase"
            try:
                response_text = await _call_guide_inline(routing_result, user_msg.user_id)
            except Exception:
                response_text = routing_result.get("user_response") or "How can I help you today?"

        elif action == LiaisonAction.ACKNOWLEDGE.value:
            # For acknowledge, also try to get a meaningful response from Guide
            try:
                response_text = await _call_guide_inline(routing_result, user_msg.user_id)
            except Exception:
                response_text = routing_result.get("user_response") or "Hello! I'm your HR assistant. How can I help you today?"

        else:  # fallback
            response_text = routing_result.get("user_response") or "I'm here to help. What would you like to know?"
        
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

async def _call_guide_inline(routing_result: dict, user_id: str) -> str:
    """Call Guide Agent synchronously and return the answer text directly."""
    workflow_id = routing_result.get("workflow_id")
    tenant_id   = routing_result.get("tenant_id", "")
    payload     = routing_result.get("payload", {})
    action      = routing_result.get("action", "route_to_guide")
    sd          = payload.get("structured_data", {})
    conv_key    = f"{tenant_id}_{workflow_id or user_id or 'default'}"
    history     = liaison_agent._load_history(conv_key)
    context_summary = _summarize_recent_user_context(history)
    original_message = payload.get("original_message", "")

    if action == LiaisonAction.ROUTE_LEAVE_REQUEST.value:
        leave_type = sd.get("leave_type", "casual")
        start_date = sd.get("start_date", "")
        end_date   = sd.get("end_date", start_date)
        num_days   = sd.get("num_days", 1)
        reason     = sd.get("reason", "personal reasons")
        emp_id     = sd.get("employee_id") or user_id
        emp_email  = sd.get("employee_email") or (user_id if "@" in str(user_id) else "")

        # If classifier lost dates (e.g. follow-up message only says "earned leave"),
        # recover them from the recent conversation context.
        if _is_placeholder_date(start_date) or _is_placeholder_date(end_date):
            combined = "\n".join([context_summary, original_message])
            extracted_dates = _extract_dates_from_text(combined)
            if len(extracted_dates) >= 2:
                start_date = extracted_dates[0].strftime("%Y-%m-%d")
                end_date = extracted_dates[1].strftime("%Y-%m-%d")
                delta = (extracted_dates[1].date() - extracted_dates[0].date()).days
                num_days = max(1, delta + 1)
            elif len(extracted_dates) == 1:
                start_date = extracted_dates[0].strftime("%Y-%m-%d")
                end_date = start_date
                num_days = 1

        short_context = context_summary or original_message
        query = (
            f"I need to apply {leave_type} leave from {start_date} to {end_date} "
            f"({num_days} day(s)) for {reason}. "
            f"My employee ID is {emp_id} and email is {emp_email}. "
            f"Conversation context summary for HR: {short_context}. "
            f"Ensure the leave submission keeps exact dates and a concise reason summary."
        )
    elif action == LiaisonAction.ROUTE_ONBOARDING.value:
        emp_id = sd.get("employee_id") or user_id
        query  = f"Show my onboarding journey progress. My employee ID is {emp_id}."
    else:
        query = original_message

    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            f"{settings.guide_agent_url}/query",
            json={
                "query":       query,
                "company_id":  tenant_id,
                "session_id":  workflow_id,
                "employee_id": sd.get("employee_id") or user_id,
            }
        )
        r.raise_for_status()
        answer = r.json().get("answer") or r.json().get("response") or "I could not find a specific answer for that."

    logger.info(f"Guide Agent answered inline [{action}] for user {user_id}")
    return answer


async def _call_hr_action_inline(routing_result: dict, user_id: str) -> str:
    """Handle HR management actions inline and return the answer text."""
    tenant_id = routing_result.get("tenant_id", "")
    sd        = routing_result.get("payload", {}).get("structured_data", {})
    hr_action = sd.get("hr_action_type", "")
    base      = settings.orchestrator_agent_url

    if hr_action == "schedule_meeting":
        # Schedule a meeting via orchestrator → scheduler pipeline
        intern_email  = sd.get("intern_email", "")
        intern_name   = sd.get("intern_name", intern_email.split("@")[0] if intern_email else "Intern")
        date          = sd.get("date", "")
        time_slot     = sd.get("time", "10:00")
        duration_mins = sd.get("duration_mins", 60)
        title         = sd.get("title", "HR Meeting")
        hr_email      = sd.get("hr_email", user_id)

        if not intern_email or not date:
            return (
                "I need the intern's email address and the meeting date to schedule a meeting. "
                "Please provide them: e.g. 'Schedule a meet with alex@gmail.com on March 20 at 2pm'"
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{base}/meetings/schedule",
                json={
                    "tenant_id":    tenant_id,
                    "hr_email":     hr_email,
                    "intern_email": intern_email,
                    "intern_name":  intern_name,
                    "date":         date,
                    "time":         time_slot,
                    "duration_mins": duration_mins,
                    "title":        title,
                }
            )
            r.raise_for_status()
            data = r.json()

        meeting_id = data.get("meeting_id", "")
        answer = (
            f"✅ Meeting request submitted!\n\n"
            f"**Details:**\n"
            f"• With: {intern_name} ({intern_email})\n"
            f"• Date: {date} at {time_slot}\n"
            f"• Duration: {duration_mins} minutes\n"
            f"• Title: {title}\n\n"
            f"The Google Meet link will be created by the scheduler and will appear in your calendar shortly. "
            f"A calendar invite will also be sent to {intern_email}."
        )
        logger.info(f"Meeting scheduled via orchestrator: {meeting_id}")
        return answer

    async with httpx.AsyncClient(timeout=30.0) as client:
        if hr_action == "view_leave_requests":
            r = await client.get(f"{base}/leave/requests", params={"tenant_id": tenant_id, "status": "PENDING"})
            r.raise_for_status()
            data   = r.json()
            answer = f"There are {len(data.get('leave_requests', []))} pending leave requests.\n"
            for req in data.get("leave_requests", [])[:10]:
                answer += (
                    f"• {req.get('employee_name')} — {req.get('leave_type')} leave | "
                    f"{req.get('start_date')} to {req.get('end_date')} | {req.get('reason', '')}\n"
                )
        elif hr_action == "view_onboarding":
            r = await client.get(f"{base}/onboarding/journeys", params={"tenant_id": tenant_id})
            r.raise_for_status()
            data   = r.json()
            answer = f"There are {data.get('total', 0)} onboarding journeys.\n"
            for j in data.get("journeys", [])[:10]:
                answer += (
                    f"• {j.get('employee_name')} — Day {j.get('current_day')}/3 | "
                    f"Progress: {j.get('progress_pct')}%\n"
                )
        else:
            answer = f"HR action '{hr_action}' received. Please use the HR Dashboard for detailed management."

    logger.info(f"HR action '{hr_action}' handled inline for tenant {tenant_id}")
    return answer


async def _route_to_guide(routing_result: dict, user_id: str):
    """Call Guide Agent directly via HTTP and store the response.

    Handles 3 action types:
    - route_to_guide      → plain policy query
    - route_leave_request → autonomous leave approval workflow
    - route_onboarding_journey → onboarding progress query
    """
    try:
        workflow_id = routing_result.get("workflow_id")
        tenant_id   = routing_result.get("tenant_id", "")
        payload     = routing_result.get("payload", {})
        action      = routing_result.get("action", "route_to_guide")
        sd          = payload.get("structured_data", {})

        # Build the query string passed to Guide Agent
        if action == LiaisonAction.ROUTE_LEAVE_REQUEST.value:
            leave_type  = sd.get("leave_type", "casual")
            start_date  = sd.get("start_date", "")
            end_date    = sd.get("end_date", start_date)
            num_days    = sd.get("num_days", 1)
            reason      = sd.get("reason", "personal reasons")
            emp_id      = sd.get("employee_id") or user_id
            emp_email   = sd.get("employee_email", "")
            emp_name    = sd.get("employee_name", user_id)
            query = (
                f"I need to apply {leave_type} leave from {start_date} to {end_date} "
                f"({num_days} day(s)) for {reason}. "
                f"My employee ID is {emp_id} and email is {emp_email}."
            )
        elif action == LiaisonAction.ROUTE_ONBOARDING.value:
            emp_id = sd.get("employee_id") or user_id
            query = f"Show my onboarding journey progress. My employee ID is {emp_id}."
        else:
            query = payload.get("original_message", "")

        context = {
            "employee_id":    sd.get("employee_id") or user_id,
            "employee_name":  sd.get("employee_name", user_id),
            "employee_email": sd.get("employee_email", ""),
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                f"{settings.guide_agent_url}/query",
                json={
                    "query":      query,
                    "company_id": tenant_id,
                    "session_id": workflow_id,
                    "employee_id": context.get("employee_id"),
                }
            )
            r.raise_for_status()
            answer = r.json().get("answer", "I could not find a specific answer for that.")

        liaison_agent.process_guide_response(
            guide_response=answer,
            tenant_id=tenant_id,
            workflow_id=workflow_id or "",
            original_query=query,
        )
        logger.info(f"Guide Agent answered [{action}] for workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Error routing to Guide Agent: {e}")


async def _handle_hr_action(routing_result: dict, user_id: str):
    """Handle HR management actions by calling Orchestrator REST endpoints."""
    try:
        tenant_id = routing_result.get("tenant_id", "")
        sd        = routing_result.get("payload", {}).get("structured_data", {})
        hr_action = sd.get("hr_action_type", "")

        base = settings.orchestrator_agent_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            if hr_action == "view_leave_requests":
                r = await client.get(f"{base}/leave/requests", params={"tenant_id": tenant_id, "status": "PENDING"})
                r.raise_for_status()
                data = r.json()
                answer = f"Pending leave requests: {len(data.get('leave_requests', []))} found.\n"
                for req in data.get("leave_requests", [])[:10]:
                    answer += (
                        f"  [{req.get('request_id')}] {req.get('employee_name')} — "
                        f"{req.get('leave_type')} | {req.get('start_date')} to {req.get('end_date')} | "
                        f"{req.get('reason', '')}\n"
                    )
            elif hr_action == "view_onboarding":
                r = await client.get(f"{base}/onboarding/journeys", params={"tenant_id": tenant_id})
                r.raise_for_status()
                data = r.json()
                answer = f"Onboarding journeys: {data.get('total', 0)} employee(s).\n"
                for j in data.get("journeys", [])[:10]:
                    answer += (
                        f"  [{j.get('employee_id')}] {j.get('employee_name')} — "
                        f"Day {j.get('current_day')}/3 | Progress: {j.get('progress_pct')}%\n"
                    )
            else:
                answer = f"HR action '{hr_action}' received. Please use the HR Dashboard for detailed management."

        wf_id = routing_result.get("workflow_id", "")
        liaison_agent.process_guide_response(
            guide_response=answer,
            tenant_id=tenant_id,
            workflow_id=wf_id,
            original_query=hr_action,
        )
        logger.info(f"HR action '{hr_action}' handled for tenant {tenant_id}")

    except Exception as e:
        logger.error(f"Error handling HR action: {e}")


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
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        workers=settings.api_workers
    )
