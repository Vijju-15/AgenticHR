"""FastAPI application for Orchestrator Agent."""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from pathlib import Path
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.database.db import init_db
from src.schemas.mcp_message import OnboardingInitiation, TaskResult
from src.schemas.workflow import Workflow
from src.agent.orchestrator import orchestrator_agent
from src.messaging.redis_client import redis_client

# Create logs directory
Path("logs").mkdir(exist_ok=True)

_START_TIME = time.time()

# Configure logging
logger.add(
    settings.log_file,
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Initialize FastAPI app
app = FastAPI(
    title="Orchestrator Agent",
    description="Central workflow orchestration agent for AgenticHR",
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


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API-key guard. Skipped when AGENTHR_API_KEY is not configured."""
    skip_paths = ("/health", "/metrics", "/docs", "/openapi.json", "/")
    if settings.api_key and not any(request.url.path.startswith(p) for p in skip_paths):
        key = request.headers.get("X-API-Key", "")
        if key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting Orchestrator Agent")
    init_db()
    logger.info("Database initialized")
    asyncio.create_task(_redis_result_listener())
    logger.info("Redis result listener started")


async def _redis_result_listener():
    """
    Background loop: reads TaskResult messages published by sub-agents
    (Scheduler, Provisioning, …) from agent_stream:orchestrator_agent
    and forwards them to handle_task_result.
    """
    from src.schemas.mcp_message import MessageType, AgentType
    AGENT_NAME = "orchestrator_agent"
    STREAM     = f"agent_stream:{AGENT_NAME}"
    GROUP      = f"{AGENT_NAME}_group"

    logger.info(f"[redis-listener] Listening on {STREAM}")
    while True:
        try:
            messages = redis_client.read_messages(
                agent_name=AGENT_NAME, count=10, block=1000
            )
            for msg_id, mcp_msg in messages:
                try:
                    if mcp_msg.message_type == MessageType.TASK_RESULT:
                        d = mcp_msg.data or {}
                        task_result = TaskResult(
                            task_id       = d.get("task_id", ""),
                            workflow_id   = mcp_msg.workflow_id or "",
                            tenant_id     = mcp_msg.tenant_id  or "",
                            from_agent    = mcp_msg.from_agent,
                            status        = d.get("status", "failure"),
                            result        = d.get("result") or {},
                            error         = d.get("error"),
                            retry_possible= d.get("retry_possible", True),
                        )
                        logger.info(
                            f"[redis-listener] Processing task result "
                            f"{task_result.task_id} status={task_result.status}"
                        )
                        orchestrator_agent.handle_task_result(task_result)
                    else:
                        logger.debug(
                            f"[redis-listener] Ignoring message type "
                            f"{mcp_msg.message_type.value}"
                        )
                    # Acknowledge so it isn't re-delivered
                    redis_client.acknowledge_message(STREAM, GROUP, msg_id)
                except Exception as exc:
                    logger.error(f"[redis-listener] Error processing {msg_id}: {exc}")
        except asyncio.CancelledError:
            logger.info("[redis-listener] Cancelled – shutting down")
            break
        except Exception as exc:
            logger.error(f"[redis-listener] Unexpected error: {exc}")
            await asyncio.sleep(1)
        await asyncio.sleep(0.01)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "orchestrator-agent",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def get_metrics():
    """Runtime metrics for the Orchestrator Agent."""
    from src.database.db import get_db
    workflow_count = 0
    try:
        with get_db() as db:
            workflow_count = db.workflows.count_documents({})
    except Exception:
        pass
    return {
        "agent": "orchestrator_agent",
        "uptime_seconds": int(time.time() - _START_TIME),
        "redis_connected": redis_client.health_check(),
        "total_workflows": workflow_count,
        "stream_info": redis_client.get_stream_info("orchestrator_agent")
    }


@app.post("/onboarding/initiate", response_model=Workflow)
async def initiate_onboarding(request: OnboardingInitiation):
    """
    Initiate new onboarding workflow.
    
    This endpoint:
    1. Creates a new workflow
    2. Decomposes it into tasks using Gemini
    3. Delegates tasks to appropriate agents
    """
    try:
        logger.info(f"Initiating onboarding for {request.employee_name} at tenant {request.tenant_id}")
        workflow = orchestrator_agent.initiate_onboarding(request)
        return workflow
    except Exception as e:
        logger.error(f"Error initiating onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/result")
async def receive_task_result(task_result: TaskResult):
    """
    Receive task completion result from agents.
    
    Agents send task results here after completing delegated tasks.
    """
    try:
        logger.info(f"Received task result for {task_result.task_id}")
        orchestrator_agent.handle_task_result(task_result)
        return {"status": "received", "task_id": task_result.task_id}
    except Exception as e:
        logger.error(f"Error processing task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details."""
    from src.database.db import get_db
    
    try:
        with get_db() as db:
            workflow_doc = db.workflows.find_one({"workflow_id": workflow_id})
            
            if not workflow_doc:
                raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
            
            tasks = list(db.tasks.find({"workflow_id": workflow_id}))
            
            return {
                "workflow_id": workflow_doc["workflow_id"],
                "tenant_id": workflow_doc["tenant_id"],
                "employee_id": workflow_doc["employee_id"],
                "employee_name": workflow_doc["employee_name"],
                "employee_email": workflow_doc["employee_email"],
                "role": workflow_doc["role"],
                "department": workflow_doc["department"],
                "start_date": workflow_doc["start_date"],
                "status": workflow_doc["status"],
                "created_at": workflow_doc["created_at"].isoformat(),
                "updated_at": workflow_doc["updated_at"].isoformat(),
                "completed_at": workflow_doc["completed_at"].isoformat() if workflow_doc.get("completed_at") else None,
                "metadata": workflow_doc.get("metadata", {}),
                "tasks": [
                    {
                        "task_id": task["task_id"],
                        "task_type": task["task_type"],
                        "assigned_agent": task["assigned_agent"],
                        "status": task["status"],
                        "payload": task.get("payload", {}),
                        "result": task.get("result"),
                        "error": task.get("error"),
                        "retry_count": task.get("retry_count", 0),
                        "created_at": task["created_at"].isoformat(),
                        "completed_at": task["completed_at"].isoformat() if task.get("completed_at") else None
                    }
                    for task in tasks
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows")
async def list_workflows(tenant_id: str = None, limit: int = 50):
    """List workflows."""
    from src.database.db import get_db
    
    try:
        with get_db() as db:
            query_filter = {"tenant_id": tenant_id} if tenant_id else {}
            
            workflows = list(
                db.workflows.find(query_filter)
                .sort("created_at", -1)
                .limit(limit)
            )
            
            return [
                {
                    "workflow_id": wf["workflow_id"],
                    "tenant_id": wf["tenant_id"],
                    "employee_name": wf["employee_name"],
                    "status": wf["status"],
                    "created_at": wf["created_at"].isoformat()
                }
                for wf in workflows
            ]
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str = "acme_corp"


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = Field(..., pattern="^(hr|employee)$")
    department: Optional[str] = None
    tenant_id: str = "acme_corp"


_bearer = HTTPBearer(auto_error=False)


def _get_db():
    from src.database.db import get_db as _gdb
    with _gdb() as d:
        return d


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT."""
    from src.database.db import get_db as _gdb
    from src.models.auth_model import verify_password, create_token, UserRecord, TokenResponse

    try:
        with _gdb() as db:
            doc = db.users.find_one({"tenant_id": req.tenant_id, "email": req.email.lower()})
            if not doc or not verify_password(req.password, doc["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            user = UserRecord(
                user_id=doc["user_id"],
                tenant_id=doc["tenant_id"],
                email=doc["email"],
                full_name=doc["full_name"],
                role=doc["role"],
                department=doc.get("department"),
                password_hash=doc["password_hash"],
            )
            token = create_token(user)
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": user.role,
                "user_id": user.user_id,
                "full_name": user.full_name,
                "tenant_id": user.tenant_id,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user account."""
    from src.database.db import get_db as _gdb
    from src.models.auth_model import hash_password, user_to_dict, UserRecord

    try:
        with _gdb() as db:
            if db.users.find_one({"tenant_id": req.tenant_id, "email": req.email.lower()}):
                raise HTTPException(status_code=409, detail="Email already registered")

            user_id = f"usr_{uuid.uuid4().hex[:10]}"
            user = UserRecord(
                user_id=user_id,
                tenant_id=req.tenant_id,
                email=req.email.lower(),
                full_name=req.full_name,
                role=req.role,
                department=req.department,
                password_hash=hash_password(req.password),
            )
            db.users.insert_one(user_to_dict(user))
            return {"status": "registered", "user_id": user_id, "role": req.role}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Verify JWT and return decoded claims."""
    from src.models.auth_model import decode_token
    import jwt as _jwt

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        claims = decode_token(credentials.credentials)
        return {"valid": True, "claims": claims}
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except _jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class LeaveRequestCreate(BaseModel):
    tenant_id: str
    employee_id: str
    employee_name: str
    employee_email: str
    leave_type: str = "casual"
    start_date: str
    end_date: str
    num_days: float
    reason: str
    hr_email: Optional[str] = None


class LeaveDecision(BaseModel):
    approver_id: str
    decision: str = Field(..., pattern="^(approved|rejected)$")
    approver_note: Optional[str] = None


def _canonical_tenant_id(raw_tenant: str) -> str:
    """Normalize known tenant aliases to a canonical id used across dashboards."""
    value = (raw_tenant or "").strip()
    key = value.lower().replace("-", " ").replace("_", " ")
    key = " ".join(key.split())
    alias_map = {
        "acme corporation": "acme_corp",
        "acme corp": "acme_corp",
        "acme": "acme_corp",
        "acme corp.": "acme_corp",
    }
    return alias_map.get(key, value)


def _tenant_query_candidates(raw_tenant: str) -> list[str]:
    """Build candidate tenant ids for backwards-compatible read queries."""
    canonical = _canonical_tenant_id(raw_tenant)
    candidates = {raw_tenant, canonical}
    if canonical == "acme_corp":
        candidates.update({"Acme Corporation", "acme corporation", "Acme Corp", "acme corp"})
    return [c for c in candidates if c]


def _normalize_reason_text(text: Optional[str]) -> str:
    return " ".join((text or "").strip().lower().split())


@app.post("/leave/requests")
async def create_leave_request(req: LeaveRequestCreate):
    """Create a new leave request (submitted by employee or Guide Agent)."""
    from src.database.db import get_db as _gdb
    from src.models.leave_model import leave_request_to_dict, LeaveStatus

    canonical_tenant_id = _canonical_tenant_id(req.tenant_id)
    normalized_email = (req.employee_email or "").strip().lower()
    normalized_employee_id = (req.employee_id or "").strip()
    normalized_leave_type = (req.leave_type or "casual").strip().lower()
    normalized_reason = (req.reason or "").strip()
    normalized_reason_key = _normalize_reason_text(normalized_reason)

    request_id = f"LR_{canonical_tenant_id}_{uuid.uuid4().hex[:8]}"
    doc = leave_request_to_dict(
        request_id=request_id,
        tenant_id=canonical_tenant_id,
        employee_id=normalized_employee_id,
        employee_name=req.employee_name,
        employee_email=normalized_email,
        leave_type=normalized_leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        num_days=req.num_days,
        reason=normalized_reason,
        status=LeaveStatus.PENDING,
        hr_email=req.hr_email,
    )
    try:
        with _gdb() as db:
            duplicate_query: dict = {
                "tenant_id": {"$in": _tenant_query_candidates(canonical_tenant_id)},
                "status": "PENDING",
                "leave_type": normalized_leave_type,
                "start_date": req.start_date,
                "end_date": req.end_date,
                "num_days": float(req.num_days),
            }

            if normalized_email:
                duplicate_query["employee_email"] = normalized_email
            elif normalized_employee_id:
                duplicate_query["employee_id"] = normalized_employee_id

            existing_candidates = list(
                db.leave_requests.find(duplicate_query)
                .sort("created_at", -1)
                .limit(10)
            )

            for existing in existing_candidates:
                if _normalize_reason_text(existing.get("reason")) == normalized_reason_key:
                    logger.info(
                        f"Duplicate leave request blocked for {normalized_email or normalized_employee_id}: "
                        f"existing {existing.get('request_id')}"
                    )
                    return {
                        "request_id": existing.get("request_id"),
                        "status": existing.get("status", "PENDING"),
                        "message": "A matching leave request is already pending HR approval.",
                        "duplicate": True,
                    }

            db.leave_requests.insert_one(doc)
        logger.info(f"Leave request {request_id} created for {req.employee_name}")
        return {"request_id": request_id, "status": "PENDING", "message": "Leave request submitted and pending HR approval."}
    except Exception as e:
        logger.error(f"Error creating leave request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leave/requests")
async def list_leave_requests(
    tenant_id: str,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    employee_email: Optional[str] = None,
    limit: int = 50,
):
    """List leave requests (HR can filter by status; employees by employee_id)."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            tenant_candidates = _tenant_query_candidates(tenant_id)
            q: dict = {"tenant_id": {"$in": tenant_candidates}}
            if status:
                q["status"] = status.upper()
            if employee_id:
                q["employee_id"] = employee_id
            if employee_email:
                q["employee_email"] = employee_email

            raw_docs = list(db.leave_requests.find(q).sort("created_at", -1).limit(limit))

            # Collapse accidental duplicate pending requests (same employee + dates + reason + type).
            docs = []
            seen_pending_keys = set()
            for d in raw_docs:
                if d.get("status") == "PENDING":
                    key = (
                        (d.get("employee_email") or "").strip().lower(),
                        (d.get("employee_id") or "").strip().lower(),
                        (d.get("leave_type") or "").strip().lower(),
                        d.get("start_date"),
                        d.get("end_date"),
                        float(d.get("num_days") or 0),
                        _normalize_reason_text(d.get("reason")),
                    )
                    if key in seen_pending_keys:
                        continue
                    seen_pending_keys.add(key)
                docs.append(d)

            for d in docs:
                d.pop("_id", None)
                if d.get("created_at"):
                    d["created_at"] = d["created_at"].isoformat()
                if d.get("updated_at"):
                    d["updated_at"] = d["updated_at"].isoformat()
                if d.get("decided_at"):
                    d["decided_at"] = d["decided_at"].isoformat()
            return {"leave_requests": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"Error listing leave requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/leave/requests/{request_id}/decision")
async def decide_leave_request(
    request_id: str,
    decision: LeaveDecision,
    background_tasks: BackgroundTasks,
):
    """HR approves or rejects a leave request, then fires a leave-notification webhook."""
    from src.database.db import get_db as _gdb
    import os, httpx

    try:
        with _gdb() as db:
            doc = db.leave_requests.find_one({"request_id": request_id})
            if not doc:
                # Backward compatibility for legacy IDs generated with tenant display names.
                legacy_aliases = [
                    request_id.replace("LR_Acme Corporation_", "LR_acme_corp_"),
                    request_id.replace("LR_Acme Corp_", "LR_acme_corp_"),
                    request_id.replace("LR_acme corporation_", "LR_acme_corp_"),
                ]
                for alt in legacy_aliases:
                    if alt != request_id:
                        doc = db.leave_requests.find_one({"request_id": alt})
                        if doc:
                            break
            if not doc:
                raise HTTPException(status_code=404, detail="Leave request not found")
            if doc["status"] != "PENDING":
                raise HTTPException(status_code=400, detail=f"Request already {doc['status']}")

            new_status = decision.decision.upper()
            resolved_request_id = doc.get("request_id", request_id)
            db.leave_requests.update_one(
                {"request_id": resolved_request_id},
                {"$set": {
                    "status":        new_status,
                    "approver_id":   decision.approver_id,
                    "approver_note": decision.approver_note,
                    "updated_at":    datetime.now(timezone.utc),
                    "decided_at":    datetime.now(timezone.utc),
                }},
            )
            logger.info(f"Leave request {resolved_request_id} {new_status} by {decision.approver_id}")

            # Fire leave-decision notification via n8n (non-blocking)
            notification_payload = {
                "request_id":     request_id,
                "employee_name":  doc.get("employee_name", ""),
                "employee_email": doc.get("employee_email", ""),
                "leave_type":     doc.get("leave_type", ""),
                "start_date":     doc.get("start_date", ""),
                "end_date":       doc.get("end_date", ""),
                "num_days":       doc.get("num_days", 0),
                "decision":       new_status,
                "approver_note":  decision.approver_note or "",
                "tenant_id":      doc.get("tenant_id", ""),
            }
            n8n_base = os.getenv("N8N_WEBHOOK_BASE_URL", "http://localhost:5678/webhook")

            async def _fire_notification(payload: dict, url: str):
                try:
                    async with httpx.AsyncClient(timeout=8) as client:
                        await client.post(url, json=payload)
                    logger.info(f"Leave notification sent to n8n for request {request_id}")
                except Exception as ex:
                    logger.warning(f"Leave notification webhook failed (non-critical): {ex}")

            background_tasks.add_task(_fire_notification, notification_payload, f"{n8n_base}/leave-notification")

            return {
                "request_id": request_id,
                "status":     new_status,
                "message":    f"Leave request {new_status.lower()} successfully.",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deciding leave request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leave/requests/{request_id}")
async def get_leave_request(request_id: str):
    """Get a single leave request."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            doc = db.leave_requests.find_one({"request_id": request_id})
            if not doc:
                raise HTTPException(status_code=404, detail="Leave request not found")
            doc.pop("_id", None)
            for f in ("created_at", "updated_at", "decided_at"):
                if doc.get(f):
                    doc[f] = doc[f].isoformat()
            return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ONBOARDING JOURNEY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class JourneyCreate(BaseModel):
    tenant_id: str
    employee_id: str
    employee_name: str
    employee_email: str
    start_date: str


class StepComplete(BaseModel):
    step_id: str
    status: str = "COMPLETED"   # COMPLETED | SKIPPED


@app.post("/onboarding/journey")
async def create_journey(req: JourneyCreate):
    """Create a structured onboarding journey for a new hire."""
    from src.database.db import get_db as _gdb
    from src.models.journey_model import journey_to_dict

    journey_id = f"JRN_{req.tenant_id}_{req.employee_id}_{uuid.uuid4().hex[:6]}"
    doc = journey_to_dict(
        journey_id=journey_id,
        tenant_id=req.tenant_id,
        employee_id=req.employee_id,
        employee_name=req.employee_name,
        employee_email=req.employee_email,
        start_date=req.start_date,
    )
    try:
        with _gdb() as db:
            # Upsert — one journey per employee per tenant
            existing = db.onboarding_journeys.find_one({
                "tenant_id": req.tenant_id, "employee_id": req.employee_id
            })
            if existing:
                return {"journey_id": existing["journey_id"], "status": "already_exists"}
            db.onboarding_journeys.insert_one(doc)
        logger.info(f"Onboarding journey {journey_id} created for {req.employee_name}")
        return {"journey_id": journey_id, "status": "created"}
    except Exception as e:
        logger.error(f"Error creating journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/onboarding/journey/{employee_id}")
async def get_journey(employee_id: str, tenant_id: str):
    """Get onboarding journey progress for an employee."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            doc = db.onboarding_journeys.find_one({
                "tenant_id": tenant_id, "employee_id": employee_id
            })
            if not doc:
                raise HTTPException(status_code=404, detail="Journey not found")
            doc.pop("_id", None)
            for f in ("created_at", "updated_at", "completed_at"):
                if doc.get(f):
                    doc[f] = doc[f].isoformat()
            return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/onboarding/journeys")
async def list_journeys(tenant_id: str, limit: int = 50):
    """List all onboarding journeys for a tenant (HR view)."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            docs = list(
                db.onboarding_journeys.find({"tenant_id": tenant_id})
                .sort("created_at", -1).limit(limit)
            )
            results = []
            for d in docs:
                d.pop("_id", None)
                for f in ("created_at", "updated_at", "completed_at"):
                    if d.get(f):
                        d[f] = d[f].isoformat()
                results.append({
                    "journey_id":   d["journey_id"],
                    "employee_id":  d["employee_id"],
                    "employee_name":d["employee_name"],
                    "start_date":   d["start_date"],
                    "current_day":  d["current_day"],
                    "progress_pct": d["overall_progress_pct"],
                    "created_at":   d.get("created_at"),
                })
            return {"journeys": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/onboarding/journey/{employee_id}/complete-step")
async def complete_step(employee_id: str, tenant_id: str, payload: StepComplete):
    """Mark an onboarding step as completed or skipped."""
    from src.database.db import get_db as _gdb
    from src.models.journey_model import _calc_progress

    try:
        with _gdb() as db:
            doc = db.onboarding_journeys.find_one({
                "tenant_id": tenant_id, "employee_id": employee_id
            })
            if not doc:
                raise HTTPException(status_code=404, detail="Journey not found")

            # Update the step
            plan = doc["plan"]
            found = False
            for day in plan:
                for step in day["steps"]:
                    if step["step_id"] == payload.step_id:
                        step["status"] = payload.status
                        found = True
            if not found:
                raise HTTPException(status_code=404, detail=f"step_id '{payload.step_id}' not found")

            progress = _calc_progress(plan)
            # Update current_day to first day with pending steps
            current_day = doc["current_day"]
            for day in plan:
                has_pending = any(s["status"] == "PENDING" for s in day["steps"])
                if has_pending:
                    current_day = day["day"]
                    break

            db.onboarding_journeys.update_one(
                {"tenant_id": tenant_id, "employee_id": employee_id},
                {"$set": {
                    "plan": plan,
                    "overall_progress_pct": progress,
                    "current_day": current_day,
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            return {"step_id": payload.step_id, "status": payload.status, "progress_pct": progress}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# INBOX / EMAIL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class EmailMarkRead(BaseModel):
    email_id: str


@app.get("/emails")
async def list_emails(
    tenant_id: str,
    dashboard_target: Optional[str] = None,   # "hr" | "employee"
    status: Optional[str] = None,              # "unread" | "read" | "processed"
    limit: int = 50,
):
    """List emails for a given dashboard (HR or Employee/Intern)."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            q: dict = {"tenant_id": tenant_id}
            if dashboard_target:
                q["dashboard_target"] = dashboard_target
            if status:
                q["status"] = status
            docs = list(db.emails.find(q).sort("received_at", -1).limit(limit))
            for d in docs:
                d.pop("_id", None)
                if d.get("received_at"):
                    d["received_at"] = d["received_at"].isoformat()
            return {"emails": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/emails/{email_id}/read")
async def mark_email_read(email_id: str):
    """Mark an email as read."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            result = db.emails.update_one(
                {"email_id": email_id},
                {"$set": {"status": "read", "read_at": datetime.now(timezone.utc)}},
            )
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Email not found")
            return {"email_id": email_id, "status": "read"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emails/seed")
async def seed_emails(tenant_id: str = "acme_corp"):
    """Seed example emails for demo/testing purposes."""
    from src.database.db import get_db as _gdb

    examples = _build_example_emails(tenant_id)
    try:
        with _gdb() as db:
            db.emails.create_index("email_id", unique=True)
            db.emails.create_index([("tenant_id", 1), ("dashboard_target", 1)])
            inserted = 0
            for em in examples:
                result = db.emails.update_one(
                    {"email_id": em["email_id"]},
                    {"$setOnInsert": em},
                    upsert=True,
                )
                if result.upserted_id:
                    inserted += 1
            return {"seeded": inserted, "total_examples": len(examples), "tenant_id": tenant_id}
    except Exception as e:
        logger.error(f"Error seeding emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_example_emails(tenant_id: str):
    """Return a list of realistic example email documents."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    def _email(eid, from_name, from_email, to_email, subject, body, intent,
               dashboard_target, priority, hours_ago):
        return {
            "email_id":         eid,
            "tenant_id":        tenant_id,
            "from_name":        from_name,
            "from_email":       from_email,
            "to_email":         to_email,
            "subject":          subject,
            "body":             body,
            "intent":           intent,
            "dashboard_target": dashboard_target,   # "hr" | "employee"
            "priority":         priority,            # "high" | "medium" | "low"
            "status":           "unread",
            "received_at":      now - timedelta(hours=hours_ago),
        }

    return [
        # ── HR-targeted emails ─────────────────────────────────────────────
        _email(
            eid="em_hr_001",
            from_name="Sarah Mitchell",
            from_email="sarah.mitchell@acme.com",
            to_email="hr@acme.com",
            subject="New Hire Onboarding Request – Dev Team",
            body=(
                "Hi HR team,\n\n"
                "I'd like to initiate onboarding for Jordan Lee who is joining the Dev team "
                "as a Software Engineer on March 9. Please set up their accounts, access cards "
                "and assign the standard Day-1/Day-2/Day-3 journey.\n\n"
                "Best,\nSarah Mitchell\nEngineering Manager"
            ),
            intent="onboarding_request",
            dashboard_target="hr",
            priority="high",
            hours_ago=2,
        ),
        _email(
            eid="em_hr_002",
            from_name="Alex Johnson",
            from_email="intern@acme.com",
            to_email="hr@acme.com",
            subject="Leave Request – Annual Leave 10–12 March",
            body=(
                "Dear HR,\n\n"
                "I would like to apply for 3 days of annual leave from March 10 to March 12, 2026. "
                "I have ensured my deliverables are covered during my absence.\n\n"
                "Please approve at your earliest convenience.\n\n"
                "Regards,\nAlex Johnson (Intern – Engineering)"
            ),
            intent="leave_request",
            dashboard_target="hr",
            priority="medium",
            hours_ago=5,
        ),
        _email(
            eid="em_hr_003",
            from_name="IT Department",
            from_email="it@acme.com",
            to_email="hr@acme.com",
            subject="Pending Access Provisioning for 3 New Hires",
            body=(
                "Hi HR,\n\n"
                "We have 3 new hires whose access provisioning is still pending approval:\n"
                "1. Jordan Lee – Software Engineer\n"
                "2. Priya Sharma – Data Analyst\n"
                "3. Marcus Chen – Product Manager\n\n"
                "Please confirm role assignments so we can proceed with tool access setup.\n\n"
                "Thanks,\nIT Support Team"
            ),
            intent="provisioning_action",
            dashboard_target="hr",
            priority="high",
            hours_ago=8,
        ),
        _email(
            eid="em_hr_004",
            from_name="Legal & Compliance",
            from_email="legal@acme.com",
            to_email="hr@acme.com",
            subject="Policy Update – Remote Work Policy v3.2",
            body=(
                "Dear HR Team,\n\n"
                "Please find attached the updated Remote Work Policy v3.2, effective April 1, 2026. "
                "Key changes include:\n"
                "- Maximum 3 remote days per week for engineers\n"
                "- Mandatory in-office on Tuesdays\n"
                "- VPN required for all remote connections\n\n"
                "Please distribute to all employees and update the policy portal.\n\n"
                "Best,\nLegal & Compliance"
            ),
            intent="policy_update",
            dashboard_target="hr",
            priority="medium",
            hours_ago=24,
        ),
        _email(
            eid="em_hr_005",
            from_name="Finance Team",
            from_email="finance@acme.com",
            to_email="hr@acme.com",
            subject="Payroll Discrepancy – March 2026",
            body=(
                "Hi HR,\n\n"
                "We noticed a payroll discrepancy for two employees in the Engineering department. "
                "Overtime hours for Feb 25 – Mar 1 were not captured in the system.\n\n"
                "Could you please verify and approve the correction before the March 8 payroll run?\n\n"
                "Thanks,\nFinance"
            ),
            intent="hr_action",
            dashboard_target="hr",
            priority="high",
            hours_ago=36,
        ),

        # ── Employee / Intern targeted emails ──────────────────────────────
        _email(
            eid="em_emp_001",
            from_name="HR Admin",
            from_email="hr@acme.com",
            to_email="intern@acme.com",
            subject="Welcome to Acme Corp! Your Onboarding Starts Monday",
            body=(
                "Dear Alex,\n\n"
                "Welcome aboard! We're thrilled to have you join the Engineering team.\n\n"
                "Your onboarding begins Monday, March 9. Here's what to expect:\n"
                "• Day 1: HR Introduction, Policy Overview, Document Submission\n"
                "• Day 2: Manager 1-on-1, Team Welcome, Tool Access Setup\n"
                "• Day 3: Training Modules, Project Overview, First Assignment\n\n"
                "Please bring a valid photo ID and arrive by 9:00 AM at Reception.\n\n"
                "Looking forward to having you with us!\n\nBest,\nHR Team"
            ),
            intent="welcome_onboarding",
            dashboard_target="employee",
            priority="high",
            hours_ago=1,
        ),
        _email(
            eid="em_emp_002",
            from_name="IT Support",
            from_email="it@acme.com",
            to_email="intern@acme.com",
            subject="Your Acme Corp Login Credentials & Tool Access",
            body=(
                "Hi Alex,\n\n"
                "Your accounts have been set up. Here are your login details:\n\n"
                "• Corporate Email: alex.johnson@acme.com\n"
                "• Slack Workspace: acmecorp.slack.com (invite sent to personal email)\n"
                "• Jira: jira.acme.com (credentials emailed separately)\n"
                "• GitHub Org: github.com/acme-corp (invitation sent)\n"
                "• VPN: Download Cisco AnyConnect, server: vpn.acme.com\n\n"
                "Please change all temporary passwords on first login.\n\n"
                "IT Support"
            ),
            intent="tool_access",
            dashboard_target="employee",
            priority="high",
            hours_ago=3,
        ),
        _email(
            eid="em_emp_003",
            from_name="HR Admin",
            from_email="hr@acme.com",
            to_email="intern@acme.com",
            subject="Leave Request Approved – March 10–12",
            body=(
                "Hi Alex,\n\n"
                "Your leave request for March 10–12, 2026 (3 days annual leave) has been approved.\n\n"
                "Your leave balance has been updated accordingly. Please coordinate with your "
                "manager to ensure work continuity during your absence.\n\n"
                "Have a great break!\n\nBest,\nHR Team"
            ),
            intent="leave_approval",
            dashboard_target="employee",
            priority="medium",
            hours_ago=4,
        ),
        _email(
            eid="em_emp_004",
            from_name="Manager – Sarah Mitchell",
            from_email="sarah.mitchell@acme.com",
            to_email="intern@acme.com",
            subject="Your First Project Assignment",
            body=(
                "Hey Alex,\n\n"
                "Welcome to the team! I'm excited to have you on board.\n\n"
                "For your first assignment, you'll be working on the AgenticHR dashboard UI improvements. "
                "I'll walk you through the codebase in our Day-3 meeting.\n\n"
                "In the meantime, please:\n"
                "1. Clone the repo: github.com/acme-corp/agentichr\n"
                "2. Read the README and ARCHITECTURE docs\n"
                "3. Set up your local dev environment\n\n"
                "Drop me a message on Slack if you have questions!\n\nSarah"
            ),
            intent="first_assignment",
            dashboard_target="employee",
            priority="medium",
            hours_ago=6,
        ),
        _email(
            eid="em_emp_005",
            from_name="Benefits Team",
            from_email="benefits@acme.com",
            to_email="intern@acme.com",
            subject="Enroll in Your Benefits by March 15",
            body=(
                "Dear Alex,\n\n"
                "As a new Acme Corp employee, you're eligible to enroll in the following benefits:\n\n"
                "• Health Insurance (Medical, Dental, Vision)\n"
                "• Life Insurance (2x annual salary)\n"
                "• 401(k) with 4% employer match\n"
                "• Flexible Spending Account (FSA)\n"
                "• Employee Assistance Program (EAP)\n\n"
                "Please complete your enrollment at benefits.acme.com by March 15, 2026.\n\n"
                "Questions? Reply to this email or visit HR.\n\nBenefits Team"
            ),
            intent="benefits_enrollment",
            dashboard_target="employee",
            priority="medium",
            hours_ago=12,
        ),
        _email(
            eid="em_emp_006",
            from_name="Payroll",
            from_email="payroll@acme.com",
            to_email="intern@acme.com",
            subject="Action Required: Submit Bank Details for Payroll",
            body=(
                "Hi Alex,\n\n"
                "To process your first paycheck, we need your banking information.\n\n"
                "Please log in to the HR portal and navigate to Payroll > Direct Deposit "
                "to securely submit your details by March 12.\n\n"
                "Your first pay date is March 31, 2026.\n\n"
                "Regards,\nPayroll Department"
            ),
            intent="payroll_action",
            dashboard_target="employee",
            priority="high",
            hours_ago=18,
        ),
    ]



# ═══════════════════════════════════════════════════════════════════════════
# OFFER LETTER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

import os as _os
import shutil as _shutil

class OfferLetterCreate(BaseModel):
    tenant_id:       str
    workflow_id:     str
    employee_id:     str
    candidate_name:  str
    candidate_email: str
    role:            str
    department:      str
    joining_date:    str
    stipend:         str = "As per company norms"
    send_email:      bool = True


@app.post("/offers/send")
async def send_offer(req: OfferLetterCreate):
    """Create and send an offer letter to a candidate."""
    from src.database.db import get_db as _gdb
    from src.models.offer_model import offer_letter_to_dict, OfferStatus
    from src.services.email_service import send_offer_letter

    offer_id         = f"OFFER_{req.tenant_id}_{uuid.uuid4().hex[:10]}"
    acceptance_token = uuid.uuid4().hex

    doc = offer_letter_to_dict(
        offer_id=offer_id,
        tenant_id=req.tenant_id,
        workflow_id=req.workflow_id,
        employee_id=req.employee_id,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email,
        role=req.role,
        department=req.department,
        joining_date=req.joining_date,
        stipend=req.stipend,
        acceptance_token=acceptance_token,
    )

    try:
        with _gdb() as db:
            db.offer_letters.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    email_sent = False
    if req.send_email:
        email_sent = send_offer_letter(
            candidate_email=req.candidate_email,
            candidate_name=req.candidate_name,
            role=req.role,
            department=req.department,
            joining_date=req.joining_date,
            stipend=req.stipend,
            acceptance_token=acceptance_token,
        )

    logger.info(f"Offer letter {offer_id} created for {req.candidate_name}. Email sent: {email_sent}")
    return {
        "offer_id":         offer_id,
        "acceptance_token": acceptance_token,
        "status":           "PENDING_ACCEPTANCE",
        "email_sent":       email_sent,
    }


@app.get("/offers/{token}")
async def get_offer_by_token(token: str):
    """Get offer letter details by acceptance token (public — used by candidate page)."""
    from src.database.db import get_db as _gdb

    with _gdb() as db:
        doc = db.offer_letters.find_one({"acceptance_token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Offer not found")
        doc.pop("_id", None)
        for f in ("sent_at", "accepted_at", "declined_at", "created_at", "updated_at"):
            if doc.get(f):
                doc[f] = doc[f].isoformat()
        return doc


@app.post("/offers/{token}/accept")
async def accept_offer(token: str):
    """Candidate accepts the offer. Triggers document request email automatically."""
    from src.database.db import get_db as _gdb
    from src.services.email_service import send_document_request

    with _gdb() as db:
        doc = db.offer_letters.find_one({"acceptance_token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Offer not found")
        if doc["status"] != "PENDING_ACCEPTANCE":
            raise HTTPException(status_code=400, detail=f"Offer already {doc['status']}")

        db.offer_letters.update_one(
            {"acceptance_token": token},
            {"$set": {
                "status":      "ACCEPTED",
                "accepted_at": datetime.now(timezone.utc),
                "updated_at":  datetime.now(timezone.utc),
            }},
        )

        # Update the workflow state to OFFER_ACCEPTED
        if doc.get("workflow_id"):
            db.workflows.update_one(
                {"workflow_id": doc["workflow_id"]},
                {"$set": {
                    "status":     "OFFER_ACCEPTED",
                    "updated_at": datetime.now(timezone.utc),
                }},
            )

    # Send document collection email
    send_document_request(
        candidate_email=doc["candidate_email"],
        candidate_name=doc["candidate_name"],
        workflow_id=doc["workflow_id"],
    )

    logger.info(f"Offer {doc['offer_id']} accepted by {doc['candidate_name']}")
    return {"status": "ACCEPTED", "message": "Offer accepted. Document upload email sent."}


@app.post("/offers/{token}/decline")
async def decline_offer(token: str):
    """Candidate declines the offer."""
    from src.database.db import get_db as _gdb

    with _gdb() as db:
        doc = db.offer_letters.find_one({"acceptance_token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Offer not found")
        if doc["status"] != "PENDING_ACCEPTANCE":
            raise HTTPException(status_code=400, detail=f"Offer already {doc['status']}")

        db.offer_letters.update_one(
            {"acceptance_token": token},
            {"$set": {
                "status":      "DECLINED",
                "declined_at": datetime.now(timezone.utc),
                "updated_at":  datetime.now(timezone.utc),
            }},
        )
        if doc.get("workflow_id"):
            db.workflows.update_one(
                {"workflow_id": doc["workflow_id"]},
                {"$set": {"status": "OFFER_DECLINED", "updated_at": datetime.now(timezone.utc)}},
            )

    logger.info(f"Offer {doc['offer_id']} declined by {doc['candidate_name']}")
    return {"status": "DECLINED", "message": "Offer declined. HR has been notified."}


@app.get("/offers")
async def list_offers(tenant_id: str, status: Optional[str] = None, limit: int = 50):
    """List all offer letters for a tenant (HR view)."""
    from src.database.db import get_db as _gdb

    with _gdb() as db:
        q: dict = {"tenant_id": tenant_id}
        if status:
            q["status"] = status.upper()
        docs = list(db.offer_letters.find(q).sort("created_at", -1).limit(limit))
        for d in docs:
            d.pop("_id", None)
            for f in ("sent_at", "accepted_at", "declined_at", "created_at", "updated_at"):
                if d.get(f):
                    d[f] = d[f].isoformat()
        return {"offers": docs, "total": len(docs)}


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT UPLOAD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import File, UploadFile, Form as FForm

UPLOAD_DIR = _os.path.join(_os.path.dirname(__file__), "..", "uploads")


@app.post("/documents/upload")
async def upload_document(
    workflow_id:    str      = FForm(...),
    employee_id:    str      = FForm(...),
    tenant_id:      str      = FForm(...),
    doc_type:       str      = FForm(...),   # govt_id | photo | certificate | other
    file:           UploadFile = File(...),
):
    """Candidate uploads a document. Saves to disk and records metadata in MongoDB."""
    from src.database.db import get_db as _gdb
    from src.models.document_model import candidate_document_to_dict, DocStatus

    allowed_types = {"application/pdf", "image/jpeg", "image/png", "image/jpg",
                     "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {file.content_type}. Allowed: PDF, JPEG, PNG, DOC, DOCX"
        )

    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    # Save file
    save_dir = _os.path.join(UPLOAD_DIR, tenant_id, employee_id)
    _os.makedirs(save_dir, exist_ok=True)

    safe_name  = f"{uuid.uuid4().hex}_{file.filename.replace(' ', '_')}"
    save_path  = _os.path.join(save_dir, safe_name)
    rel_path   = f"uploads/{tenant_id}/{employee_id}/{safe_name}"

    with open(save_path, "wb") as f_out:
        f_out.write(contents)

    doc_id = f"DOC_{tenant_id}_{uuid.uuid4().hex[:10]}"
    doc = candidate_document_to_dict(
        doc_id=doc_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        employee_id=employee_id,
        doc_type=doc_type,
        original_filename=file.filename,
        storage_path=rel_path,
        file_size_bytes=len(contents),
        status=DocStatus.UPLOADED,
    )

    try:
        with _gdb() as db:
            db.candidate_documents.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Document {doc_id} uploaded for employee {employee_id} ({doc_type})")
    return {
        "doc_id":       doc_id,
        "doc_type":     doc_type,
        "filename":     file.filename,
        "size_bytes":   len(contents),
        "status":       "uploaded",
    }


@app.get("/documents/{workflow_id}")
async def list_documents(workflow_id: str, tenant_id: str):
    """List all uploaded documents for a workflow (HR view)."""
    from src.database.db import get_db as _gdb

    with _gdb() as db:
        docs = list(db.candidate_documents.find(
            {"workflow_id": workflow_id, "tenant_id": tenant_id}
        ).sort("uploaded_at", -1))
        for d in docs:
            d.pop("_id", None)
            for f in ("uploaded_at", "updated_at"):
                if d.get(f):
                    d[f] = d[f].isoformat()
        return {"documents": docs, "total": len(docs)}


@app.put("/documents/{doc_id}/verify")
async def verify_document(doc_id: str, verified_by: str):
    """HR marks a document as verified."""
    from src.database.db import get_db as _gdb

    with _gdb() as db:
        result = db.candidate_documents.update_one(
            {"doc_id": doc_id},
            {"$set": {
                "status":      "verified",
                "verified_by": verified_by,
                "updated_at":  datetime.now(timezone.utc),
            }},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "status": "verified"}


# ═══════════════════════════════════════════════════════════════════════════
# MEETINGS ENDPOINTS  (HR-scheduled Google Meets with interns)
# ═══════════════════════════════════════════════════════════════════════════

class ScheduleMeetingRequest(BaseModel):
    tenant_id: str = "acme_corp"
    hr_email: str
    intern_email: str
    intern_name: str = ""
    date: str                    # YYYY-MM-DD
    time: str = "10:00"          # HH:MM  24-hour
    duration_mins: int = 60
    title: str = "HR Meeting"


@app.post("/meetings/schedule")
async def schedule_meeting(req: ScheduleMeetingRequest):
    """
    Schedule a Google Meet between HR and an intern.

    Flow:
      1. Create a pending meeting record in MongoDB.
      2. Push a schedule_meeting task to the Scheduler Agent via Redis.
      3. When the Scheduler completes, it sends a TaskResult back via
         /tasks/result which then updates the meeting record with the
         Google Meet link.

    Returns the meeting_id so the frontend can poll /meetings for updates.
    """
    from src.database.db import get_db as _gdb
    from src.schemas.mcp_message import AgentType, MCPMessage, MessageType, TaskPayload

    intern_name = req.intern_name or req.intern_email.split("@")[0].replace(".", " ").title()

    # Look up intern's personal email for Gmail notification
    personal_email = ""
    try:
        with _gdb() as _db_pe:
            intern_doc = _db_pe.users.find_one(
                {"email": req.intern_email.lower()},
                {"personal_email": 1, "_id": 0},
            )
            if intern_doc:
                personal_email = intern_doc.get("personal_email", "")
    except Exception as _pe_err:
        logger.warning(f"Could not look up personal_email for {req.intern_email}: {_pe_err}")

    # Build ISO datetimes
    start_iso = f"{req.date}T{req.time}:00"
    try:
        from datetime import datetime as _dt, timedelta
        _start = _dt.strptime(start_iso, "%Y-%m-%dT%H:%M:%S")
        _end   = _start + timedelta(minutes=req.duration_mins)
        end_iso = _end.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        end_iso = start_iso  # fallback

    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    task_id    = f"TASK_MTG_{uuid.uuid4().hex[:8]}"

    # Save pending meeting to MongoDB
    try:
        with _gdb() as db:
            db.meetings.insert_one({
                "meeting_id":     meeting_id,
                "tenant_id":      req.tenant_id,
                "hr_email":       req.hr_email.lower(),
                "intern_email":   req.intern_email.lower(),
                "intern_name":    intern_name,
                "title":          req.title,
                "start_datetime": start_iso,
                "end_datetime":   end_iso,
                "duration_mins":  req.duration_mins,
                "meet_link":      None,
                "event_id":       None,
                "status":         "pending",
                "task_id":        task_id,
                "created_at":     datetime.now(timezone.utc),
                "updated_at":     datetime.now(timezone.utc),
            })
        logger.info(f"Meeting {meeting_id} created (pending) for {req.intern_email}")
    except Exception as e:
        logger.error(f"Error saving meeting to MongoDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Push schedule_meeting task to Scheduler via Redis
    try:
        task = TaskPayload(
            task_id=task_id,
            task_type="schedule_meeting",
            payload={
                "meeting_id":     meeting_id,
                "meeting_title":  req.title,
                "meeting_type":   "hr_meeting",
                "start_datetime": start_iso,
                "end_datetime":   end_iso,
                "organizer_email": req.hr_email,
                "participants":   [req.intern_email, req.hr_email],
                "timezone":       "Asia/Kolkata",
                "intern_email":   req.intern_email,
                "intern_name":    intern_name,
                "hr_email":       req.hr_email,
                "personal_email": personal_email,
                "description":    f"AgenticHR: {req.title} with {intern_name}",
            },
        )
        mcp_msg = MCPMessage(
            message_id=f"MSG_{uuid.uuid4().hex[:12]}",
            workflow_id=f"WF_HR_MTG_{meeting_id}",
            tenant_id=req.tenant_id,
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=AgentType.SCHEDULER,
            message_type=MessageType.TASK_REQUEST,
            task=task,
        )
        redis_client.publish_message(mcp_msg)
        logger.info(f"schedule_meeting task {task_id} sent to Scheduler via Redis")
    except Exception as e:
        logger.warning(f"Could not push meeting task to Redis: {e}")
        # Non-fatal — the frontend can still see the pending meeting

    return {
        "meeting_id":     meeting_id,
        "status":         "pending",
        "intern_email":   req.intern_email,
        "intern_name":    intern_name,
        "start_datetime": start_iso,
        "end_datetime":   end_iso,
        "message":        "Meeting request submitted. Google Meet link will appear in your calendar shortly.",
    }


@app.get("/meetings")
async def list_meetings(
    tenant_id: str = "acme_corp",
    hr_email: Optional[str] = None,
    intern_email: Optional[str] = None,
    limit: int = 100,
):
    """
    Return all meetings for a tenant (optionally filtered by HR or intern email).
    Used by the frontend calendar to display Google Meet links.
    """
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            query: dict = {"tenant_id": tenant_id}
            if hr_email:
                query["hr_email"] = hr_email.lower()
            if intern_email:
                query["intern_email"] = intern_email.lower()

            docs = list(
                db.meetings.find(query, {"_id": 0})
                .sort("start_datetime", 1)
                .limit(limit)
                .max_time_ms(5000)
            )
            # Serialise datetimes
            for d in docs:
                for f in ("created_at", "updated_at"):
                    if d.get(f):
                        d[f] = d[f].isoformat()

            return {"meetings": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/meetings/{meeting_id}")
async def cancel_meeting(meeting_id: str):
    """Cancel / delete a pending or scheduled meeting."""
    from src.database.db import get_db as _gdb

    try:
        with _gdb() as db:
            result = db.meetings.update_one(
                {"meeting_id": meeting_id},
                {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
            )
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Meeting not found")
        return {"meeting_id": meeting_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.environment == "development"
    )

