"""Employee Setup Agent (formerly Provisioning Agent).

Responsibilities (repurposed):
- Create employee records in HRIS
- Generate unique employee IDs
- Assign departments and roles
- Send welcome credentials to new hires
- Initialize structured onboarding profiles
- Create onboarding checklists

This agent:
- Listens to Redis Streams for task assignments from Orchestrator
- Executes employee setup tasks (deterministic, no AI/LLM)
- Returns structured task results to Orchestrator
- Enforces idempotency to prevent duplicate records
"""

from typing import Dict, Any, Optional
from loguru import logger
import uuid
import re
import hashlib
from datetime import datetime, timezone

from src.config.settings import settings
from src.schemas.mcp_message import (
    MCPMessage, TaskPayload, TaskResult, AgentType, MessageType
)
from src.webhooks.n8n_client import n8n_client
from src.messaging.redis_client import redis_client


class ProvisioningAgent:
    """
    Employee Setup Agent â€” deterministic execution for new-hire setup.

    Supported task_type values:
      create_employee_record     â†’ Register employee in HRIS and MongoDB
      generate_employee_id       â†’ Generate a unique employee ID
      assign_department          â†’ Assign department and reporting manager
      send_welcome_credentials   â†’ Email welcome package with login credentials
      initialize_onboarding      â†’ Create structured onboarding profile/journey
      create_onboarding_checklistâ†’ Build Day-1/2/3 task checklist
    """

    # Track processed tasks for idempotency
    _processed_tasks: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        """Initialize Employee Setup Agent."""
        self.agent_type = AgentType.PROVISIONING
        logger.info("Employee Setup Agent initialized (deterministic mode)")

        self.task_handlers = {
            "create_employee_record":      self._handle_create_employee_record,
            "generate_employee_id":        self._handle_generate_employee_id,
            "assign_department":           self._handle_assign_department,
            "send_welcome_credentials":    self._handle_send_welcome_credentials,
            "initialize_onboarding":       self._handle_initialize_onboarding,
            "create_onboarding_checklist": self._handle_create_onboarding_checklist,
            # Pre-joining communication tasks
            "send_offer_letter":           self._handle_send_offer_letter,
            "send_document_request":       self._handle_send_document_request,
            "send_manager_introduction":   self._handle_send_manager_introduction,
            # Keep legacy aliases so existing workflows still work
            "create_hr_record":  self._handle_create_employee_record,
            "generate_id":       self._handle_generate_employee_id,
        }

    # â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def validate_task_payload(self, task: TaskPayload) -> tuple[bool, Optional[str]]:
        if not task.task_id:
            return False, "Missing required field: task_id"
        if not task.task_type:
            return False, "Missing required field: task_type"
        if task.task_type not in self.task_handlers:
            return False, f"Unknown task_type: {task.task_type}"

        p = task.payload

        if task.task_type in ("create_employee_record", "create_hr_record"):
            for f in ("employee_name", "employee_email", "role", "department"):
                if f not in p:
                    return False, f"Missing required field for {task.task_type}: {f}"

        elif task.task_type in ("generate_employee_id", "generate_id"):
            if "employee_name" not in p:
                return False, "Missing employee_name for generate_employee_id"

        elif task.task_type == "assign_department":
            for f in ("employee_id", "department"):
                if f not in p:
                    return False, f"Missing required field for assign_department: {f}"

        elif task.task_type == "send_welcome_credentials":
            for f in ("employee_id", "employee_email", "employee_name"):
                if f not in p:
                    return False, f"Missing required field for send_welcome_credentials: {f}"

        elif task.task_type in ("initialize_onboarding", "create_onboarding_checklist"):
            for f in ("employee_id", "employee_name", "employee_email"):
                if f not in p:
                    return False, f"Missing required field for {task.task_type}: {f}"

        elif task.task_type == "send_offer_letter":
            for f in ("candidate_name", "candidate_email", "role", "department", "joining_date",
                      "acceptance_token"):
                if f not in p:
                    return False, f"Missing required field for send_offer_letter: {f}"

        elif task.task_type == "send_document_request":
            for f in ("candidate_name", "candidate_email", "workflow_id"):
                if f not in p:
                    return False, f"Missing required field for send_document_request: {f}"

        elif task.task_type == "send_manager_introduction":
            for f in ("candidate_name", "candidate_email", "role", "department",
                      "manager_name", "manager_email", "joining_date"):
                if f not in p:
                    return False, f"Missing required field for send_manager_introduction: {f}"

        return True, None

    # â”€â”€ Idempotency helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def check_idempotency(self, task_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        if not settings.enable_idempotency_check:
            return None
        return self._processed_tasks.get(f"{tenant_id}:{task_id}")

    def cache_result(self, task_id: str, tenant_id: str, result: Dict[str, Any]):
        if settings.enable_idempotency_check:
            self._processed_tasks[f"{tenant_id}:{task_id}"] = result
            logger.info(f"Cached result for task {task_id}")

    # ── Mongo helpers (employee account provisioning) ──────────────────────

    @staticmethod
    def _mongo_db():
        """Return MongoDB database handle for AgenticHR user records."""
        from pymongo import MongoClient

        client = MongoClient(settings.mongodb_url)
        db = client.get_default_database()
        if db is None:
            db = client["agentichr"]
        return db

    @staticmethod
    def _name_base_slug(name: str) -> str:
        """Generate a simple email slug from employee name (first name preferred)."""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", (name or "").strip()).lower()
        parts = [p for p in cleaned.split() if p]
        if parts:
            return re.sub(r"[^a-z0-9]", "", parts[0]) or "intern"
        return "intern"

    def _generate_unique_company_email(self, db, full_name: str, domain: str) -> str:
        """
        Generate unique company email:
        pavan@acme.com, pavan2@acme.com, pavan3@acme.com, ...
        """
        base = self._name_base_slug(full_name)
        n = 1
        while True:
            local = base if n == 1 else f"{base}{n}"
            candidate = f"{local}@{domain}"
            if not db.users.find_one({"email": candidate.lower()}):
                return candidate.lower()
            n += 1

    def _upsert_employee_login_record(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create/update login-ready employee record in users collection."""
        db = self._mongo_db()

        employee_id = payload.get("employee_id") or f"EMP{uuid.uuid4().hex[:6].upper()}"
        full_name = payload.get("employee_name", "New Hire").strip()
        personal_email = payload.get("employee_email", "").strip().lower()
        role_in = (payload.get("role") or "employee").strip().lower()
        app_role = "hr" if role_in == "hr" else "employee"
        department = payload.get("department")

        # Keep domain configurable; defaults to acme.com
        domain = (settings.company_email_domain or "acme.com").strip().lower()

        # Reuse existing record for this personal email if already provisioned
        existing = db.users.find_one({"tenant_id": tenant_id, "personal_email": personal_email}) if personal_email else None
        if existing:
            employee_id = existing.get("user_id") or employee_id
            company_email = existing.get("email")
        else:
            company_email = self._generate_unique_company_email(db, full_name, domain)

        temp_password = f"Welcome@{uuid.uuid4().hex[:8]}"
        password_hash = hashlib.sha256(temp_password.encode("utf-8")).hexdigest()

        user_filter = {"_id": existing["_id"]} if existing and existing.get("_id") else {
            "tenant_id": tenant_id,
            "user_id": employee_id,
        }

        db.users.update_one(
            user_filter,
            {
                "$set": {
                    "tenant_id": tenant_id,
                    "user_id": employee_id,
                    "email": company_email,
                    "full_name": full_name,
                    "name": full_name,
                    "role": app_role,
                    "department": department,
                    "personal_email": personal_email or None,
                    "password_hash": password_hash,
                    "updated_at": datetime.now(timezone.utc),
                    "source": "provisioning_agent",
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc),
                },
            },
            upsert=True,
        )

        return {
            "employee_id": employee_id,
            "company_email": company_email,
            "personal_email": personal_email,
            "temp_password": temp_password,
            "role": app_role,
            "department": department,
        }

    # â”€â”€ Main process loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def process_task(self, message: MCPMessage) -> TaskResult:
        task       = message.task
        workflow_id = message.workflow_id
        tenant_id  = message.tenant_id

        if not task:
            logger.error("Received message without task payload")
            return self._create_error_result("unknown", workflow_id, tenant_id, "No task payload", False)

        task_id = task.task_id
        logger.info(f"Processing task {task_id} (type: {task.task_type})")

        cached = self.check_idempotency(task_id, tenant_id)
        if cached:
            logger.info(f"Task {task_id} already processed (idempotent)")
            cached.get("details", {})["duplicate_detected"] = True
            return TaskResult(
                task_id=task_id, workflow_id=workflow_id, tenant_id=tenant_id,
                from_agent=self.agent_type, status="success", result=cached, retry_possible=False
            )

        is_valid, err = self.validate_task_payload(task)
        if not is_valid:
            return self._create_error_result(task_id, workflow_id, tenant_id, err, False)

        try:
            handler = self.task_handlers[task.task_type]
            result  = await handler(tenant_id, task.payload)
            self.cache_result(task_id, tenant_id, result)
            return TaskResult(
                task_id=task_id, workflow_id=workflow_id, tenant_id=tenant_id,
                from_agent=self.agent_type, status="success", result=result, retry_possible=False
            )
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            retryable = "network" in str(e).lower() or "timeout" in str(e).lower()
            return self._create_error_result(task_id, workflow_id, tenant_id, str(e), retryable)

    # â”€â”€ Task Handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _handle_create_employee_record(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Register employee in HRIS via n8n (or fallback to in-memory)."""
        logger.info(f"Creating employee record for {payload.get('employee_name')}")
        try:
            response = await n8n_client.call_webhook("/employee-setup", {
                "task_type": "create_employee_record",
                "tenant_id": tenant_id,
                "payload":   payload,
            })
            data = response.get("data", response)
        except Exception:
            # Graceful fallback â€” generate local record
            data = {
                "employee_id":  payload.get("employee_id") or f"EMP{uuid.uuid4().hex[:6].upper()}",
                "created_at":   datetime.now(timezone.utc).isoformat(),
                "hris_system":  "local",
                "record_url":   "",
            }

        # Ensure this onboarding action creates a real login account in MongoDB.
        # This enables dashboard access using the assigned company email.
        account = self._upsert_employee_login_record(tenant_id, {
            **payload,
            "employee_id": data.get("employee_id") or payload.get("employee_id"),
        })

        return {
            "external_id":   data.get("employee_id", ""),
            "reference_url": data.get("record_url", ""),
            "details": {
                "employee_id":  account.get("employee_id") or data.get("employee_id"),
                "created_at":   data.get("created_at", datetime.now(timezone.utc).isoformat()),
                "hris_system":  data.get("hris_system", "HRIS"),
                "employee_name":  payload.get("employee_name"),
                "employee_email": account.get("company_email"),
                "personal_email": account.get("personal_email"),
                "temp_password": account.get("temp_password"),
                "role":           payload.get("role"),
                "department":     payload.get("department"),
            },
        }

    async def _handle_generate_employee_id(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a unique, formatted employee ID."""
        logger.info(f"Generating employee ID for {payload.get('employee_name')}")
        dept    = payload.get("department", "GEN")[:3].upper()
        year    = datetime.now().year
        suffix  = uuid.uuid4().hex[:4].upper()
        emp_id  = f"{dept}{year}{suffix}"
        return {
            "external_id": emp_id,
            "reference_url": "",
            "details": {
                "employee_id":   emp_id,
                "format":        f"{dept}YYYY????",
                "generated_at":  datetime.now(timezone.utc).isoformat(),
                "employee_name": payload.get("employee_name"),
            },
        }

    async def _handle_assign_department(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assign department, role, and manager to an employee record."""
        logger.info(f"Assigning department for employee {payload.get('employee_id')}")
        try:
            response = await n8n_client.call_webhook("/employee-setup", {
                "task_type": "assign_department",
                "tenant_id": tenant_id,
                "payload":   payload,
            })
            data = response.get("data", response)
        except Exception:
            data = {"assigned_at": datetime.now(timezone.utc).isoformat()}

        return {
            "external_id":   payload.get("employee_id", ""),
            "reference_url": "",
            "details": {
                "employee_id":  payload.get("employee_id"),
                "department":   payload.get("department"),
                "role":         payload.get("role"),
                "manager_id":   payload.get("manager_id"),
                "assigned_at":  data.get("assigned_at", datetime.now(timezone.utc).isoformat()),
            },
        }

    async def _handle_send_welcome_credentials(self, tenant_id: str, payload: dict) -> dict:
        """Email welcome kit with temporary credentials to the new hire."""
        from src.utils.email_utils import send_welcome_credentials as _send_creds

        logger.info(f"Sending welcome credentials for employee {payload.get('employee_id')}")

        # Ensure account exists and rotate to a fresh temporary password.
        account = self._upsert_employee_login_record(tenant_id, payload)
        company_email = account.get("company_email", "")
        personal_email = account.get("personal_email", "")
        temp_password = account.get("temp_password", "")

        email_sent = False

        # Primary path: send structured email through n8n Gmail workflow
        try:
            webhook_resp = await n8n_client.call_webhook("/welcome-credentials", {
                "task_type": "send_welcome_credentials",
                "tenant_id": tenant_id,
                "payload": {
                    "employee_id": payload.get("employee_id", ""),
                    "employee_name": payload.get("employee_name", ""),
                    "personal_email": personal_email,
                    "company_email": company_email,
                    "temp_password": temp_password,
                    "role": payload.get("role", "employee"),
                    "department": payload.get("department", ""),
                    "dashboard_url": payload.get("dashboard_url", "http://localhost:3000"),
                },
            })
            email_sent = bool(webhook_resp.get("success", True))
        except Exception as e:
            logger.warning(f"n8n welcome-credentials webhook failed, using fallback email utility: {e}")
            # Fallback: direct SMTP utility (legacy path)
            email_sent = _send_creds(
                employee_email=personal_email or payload.get("employee_email", ""),
                employee_name=payload.get("employee_name", ""),
                employee_id=payload.get("employee_id", ""),
                role=payload.get("role", ""),
                department=payload.get("department", ""),
                temp_password=temp_password,
            )

        return {
            "external_id":   payload.get("employee_id", ""),
            "reference_url": "",
            "details": {
                "employee_id":    payload.get("employee_id"),
                "employee_email": company_email,
                "personal_email": personal_email,
                "temp_password":  temp_password,
                "email_sent":     email_sent,
                "sent_at":        datetime.now(timezone.utc).isoformat(),
                "note": (
                    "Welcome credentials email sent via n8n/SMTP." if email_sent
                    else "Email failed - check n8n/SMTP settings. Share credentials manually."
                ),
            },
        }

    async def _handle_send_offer_letter(self, tenant_id: str, payload: dict) -> dict:
        """Send an offer letter to a candidate via the Orchestrator /offers/send endpoint."""
        import httpx, os
        logger.info(f"Sending offer letter to {payload.get('candidate_email')}")
        orch_url   = os.getenv("ORCHESTRATOR_AGENT_URL", "http://localhost:8001")
        email_sent = False
        offer_id   = None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(f"{orch_url}/offers/send", json={
                    "tenant_id":       tenant_id,
                    "workflow_id":     payload.get("workflow_id", ""),
                    "employee_id":     payload.get("employee_id", ""),
                    "candidate_name":  payload["candidate_name"],
                    "candidate_email": payload["candidate_email"],
                    "role":            payload["role"],
                    "department":      payload["department"],
                    "joining_date":    payload["joining_date"],
                    "stipend":         payload.get("stipend", "As per company norms"),
                    "send_email":      True,
                })
                r.raise_for_status()
                data       = r.json()
                offer_id   = data.get("offer_id")
                email_sent = data.get("email_sent", False)
        except Exception as e:
            logger.warning(f"Orchestrator /offers/send failed ({e}); offer not created in DB")

        return {
            "external_id":   offer_id or "",
            "reference_url": "",
            "details": {
                "offer_id":        offer_id,
                "candidate_email": payload.get("candidate_email"),
                "email_sent":      email_sent,
                "sent_at":         datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _handle_send_document_request(self, tenant_id: str, payload: dict) -> dict:
        """Send a document upload request email to a candidate."""
        import os
        from src.utils.email_utils import _send_email as _se
        logger.info(f"Sending document request to {payload.get('candidate_email')}")
        base_url    = os.getenv("APP_BASE_URL", "http://localhost:3000")
        workflow_id = payload.get("workflow_id", "")
        upload_url  = f"{base_url}/documents/upload/{workflow_id}"
        html = (
            "<html><body style='font-family:Arial,sans-serif;background:#f4f4f4;padding:24px'>"
            "<div style='max-width:520px;margin:auto;background:#fff;border-radius:8px;padding:32px'>"
            f"<h2 style='color:#1a1a2e'>Action Required: Upload Your Documents</h2>"
            f"<p>Dear {payload['candidate_name']},</p>"
            "<p>Please upload the following documents to complete your pre-joining formalities:</p>"
            "<ul><li>Government-issued Photo ID (Aadhaar / Passport / Driving Licence)</li>"
            "<li>Recent passport-size photograph</li>"
            "<li>Highest qualification certificate</li></ul>"
            "<div style='text-align:center;margin:24px 0'>"
            f"<a href='{upload_url}' style='background:#1a73e8;color:#fff;padding:12px 28px;"
            "border-radius:6px;text-decoration:none;font-weight:bold'>Upload Documents</a>"
            "</div>"
            "<p style='color:#888;font-size:12px'>This is an automated message from AgenticHR.</p>"
            "</div></body></html>"
        )
        email_sent = _se(payload["candidate_email"], "Document Upload Required - AgenticHR", html)
        return {
            "external_id":   workflow_id,
            "reference_url": upload_url,
            "details": {
                "candidate_email": payload.get("candidate_email"),
                "upload_url":      upload_url,
                "email_sent":      email_sent,
                "sent_at":         datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _handle_send_manager_introduction(self, tenant_id: str, payload: dict) -> dict:
        """Send a manager introduction email to the new hire."""
        from src.utils.email_utils import send_manager_introduction as _send_mgr
        logger.info(f"Sending manager intro to {payload.get('candidate_email')}")
        email_sent = _send_mgr(
            candidate_email=payload["candidate_email"],
            candidate_name=payload["candidate_name"],
            role=payload["role"],
            department=payload["department"],
            manager_name=payload["manager_name"],
            manager_email=payload["manager_email"],
            joining_date=payload["joining_date"],
        )
        return {
            "external_id":   "",
            "reference_url": "",
            "details": {
                "candidate_email": payload.get("candidate_email"),
                "manager_name":    payload.get("manager_name"),
                "email_sent":      email_sent,
                "sent_at":         datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _handle_initialize_onboarding(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create an onboarding profile + journey in the Orchestrator database."""
        logger.info(f"Initializing onboarding profile for {payload.get('employee_name')}")
        import httpx, os
        orch_url   = os.getenv("ORCHESTRATOR_AGENT_URL", "http://localhost:8001")
        start_date = payload.get("start_date", datetime.now().strftime("%Y-%m-%d"))

        journey_id = None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(f"{orch_url}/onboarding/journey", json={
                    "tenant_id":      tenant_id,
                    "employee_id":    payload["employee_id"],
                    "employee_name":  payload["employee_name"],
                    "employee_email": payload["employee_email"],
                    "start_date":     start_date,
                })
                r.raise_for_status()
                journey_id = r.json().get("journey_id")
        except Exception as e:
            logger.warning(f"Could not create journey in Orchestrator: {e}")

        return {
            "external_id":   journey_id or "",
            "reference_url": f"{orch_url}/onboarding/journey/{payload['employee_id']}",
            "details": {
                "employee_id":  payload["employee_id"],
                "journey_id":   journey_id,
                "start_date":   start_date,
                "profile_ready": journey_id is not None,
                "created_at":   datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _handle_create_onboarding_checklist(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create the Day-1/2/3 onboarding checklist (delegates to initialize_onboarding)."""
        logger.info(f"Creating onboarding checklist for {payload.get('employee_name')}")
        # Reuse initialize_onboarding â€” it creates the full journey with all steps
        journey_result = await self._handle_initialize_onboarding(tenant_id, payload)
        journey_result["details"]["checklist_type"] = "day_1_2_3_structured"
        return journey_result

    # â”€â”€ Error helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _create_error_result(self, task_id, workflow_id, tenant_id, error, retryable) -> TaskResult:
        return TaskResult(
            task_id=task_id, workflow_id=workflow_id, tenant_id=tenant_id,
            from_agent=self.agent_type, status="failure",
            result={}, error=error, retry_possible=retryable
        )

    # â”€â”€ Redis listener â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def start_listening(self):
        """Start listening to Redis stream for incoming tasks."""
        import asyncio
        logger.info("Employee Setup Agent listener started â€” waiting for messagesâ€¦")

        while True:
            try:
                messages = redis_client.read_messages(count=1, block=1000)
                if not messages:
                    await asyncio.sleep(0.1)
                    continue

                for msg in messages:
                    try:
                        message = MCPMessage(**msg['data'])
                        logger.info(f"Received task {message.message_id} from {message.from_agent}")
                        result = await self.process_task(message)
                        redis_client.publish_task_result(result)
                        logger.info(f"Task {result.task_id} completed: {result.status}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

                await asyncio.sleep(0.01)

            except KeyboardInterrupt:
                logger.info("Shutting down Employee Setup Agent...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)


# Singleton instance
provisioning_agent = ProvisioningAgent()
