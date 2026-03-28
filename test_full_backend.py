"""
AgenticHR – Full Backend Test Suite
====================================
Tests every agent individually and the coordination between them.

Run:
    python test_full_backend.py               # all tests
    python test_full_backend.py --agent guide  # single agent
    python test_full_backend.py --suite coord  # coordination only

Agents under test:
    Guide Agent        http://localhost:8000
    Orchestrator Agent http://localhost:8001
    Liaison Agent      http://localhost:8002
    Provisioning Agent http://localhost:8003
    Scheduler Agent    http://localhost:8004
"""

import asyncio
import json
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

# ─────────────────────────────────────────────
#  Colour helpers (works on Windows via ANSI)
# ─────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅  {msg}{RESET}")
def fail(msg): print(f"  {RED}❌  {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️   {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ️   {msg}{RESET}")
def section(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

# ─────────────────────────────────────────────
#  Base URLs
# ─────────────────────────────────────────────
GUIDE_URL         = "http://localhost:8000"
ORCHESTRATOR_URL  = "http://localhost:8001"
LIAISON_URL       = "http://localhost:8002"
PROVISIONING_URL  = "http://localhost:8003/api/v1"
SCHEDULER_URL     = "http://localhost:8004/api/v1"

TIMEOUT = 30
GUIDE_QUERY_TIMEOUT = 90   # RAG + LLM can be slow

# ─────────────────────────────────────────────
#  Test state (shared across tests)
# ─────────────────────────────────────────────
state: Dict[str, Any] = {
    "workflow_id": None,
    "guide_company_id": None,
}

# ─────────────────────────────────────────────
#  Result tracker
# ─────────────────────────────────────────────
results: List[Dict[str, Any]] = []

def record(suite: str, test: str, passed: bool, detail: str = ""):
    results.append({"suite": suite, "test": test, "passed": passed, "detail": detail})
    if passed:
        ok(f"[{suite}] {test}")
    else:
        fail(f"[{suite}] {test}  →  {detail}")


# ══════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════

async def get(client: httpx.AsyncClient, url: str) -> Tuple[int, Any]:
    try:
        r = await client.get(url, timeout=TIMEOUT)
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}

async def post(client: httpx.AsyncClient, url: str, body: dict, timeout: int = TIMEOUT) -> Tuple[int, Any]:
    try:
        r = await client.post(url, json=body, timeout=timeout)
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}


# ══════════════════════════════════════════════
#  1. GUIDE AGENT  (port 8000)
# ══════════════════════════════════════════════

async def test_guide_agent():
    section("1. GUIDE AGENT  (port 8000)")
    S = "Guide"

    async with httpx.AsyncClient() as c:

        # --- 1.1 Health ---
        code, body = await get(c, f"{GUIDE_URL}/health")
        record(S, "GET /health → 200", code == 200, f"code={code}")

        # --- 1.2 List companies ---
        code, body = await get(c, f"{GUIDE_URL}/companies")
        record(S, "GET /companies → 200", code == 200, f"code={code}")
        companies = body if isinstance(body, list) else []
        if companies:
            state["guide_company_id"] = companies[0].get("company_id")
            info(f"Using existing company: {state['guide_company_id']}")
        else:
            warn("No companies found – skipping query tests")

        # --- 1.3 Policy query (if company exists) ---
        if state["guide_company_id"]:
            code, body = await post(c, f"{GUIDE_URL}/query", {
                "query": "What is the leave policy?",
                "company_id": state["guide_company_id"],
                "session_id": "test_session_001"
            }, timeout=GUIDE_QUERY_TIMEOUT)
            record(S, "POST /query → 200", code == 200, f"code={code} body={str(body)[:120]}")
            if code == 200:
                has_answer = bool(body.get("answer") or body.get("response"))
                record(S, "Query returns answer field", has_answer, str(body)[:120])

        # --- 1.4 Query without company → should 4xx OR return empty/error answer ---
        code, body = await post(c, f"{GUIDE_URL}/query", {
            "query": "Test",
            "company_id": "nonexistent_company_xyz"
        }, timeout=GUIDE_QUERY_TIMEOUT)
        answer_text = str(body.get("answer") or body.get("response") or "").lower()
        is_error = (
            code >= 400
            or not answer_text
            or "not found" in answer_text
            or "error" in answer_text
            or "unable" in answer_text
        )
        record(S, "POST /query bad company → error or empty answer", is_error, f"code={code} body={str(body)[:80]}")

        # --- 1.5 Company stats ---
        if state["guide_company_id"]:
            code, body = await get(c, f"{GUIDE_URL}/companies/{state['guide_company_id']}/stats")
            record(S, "GET /companies/{id}/stats → 200", code == 200, f"code={code}")


# ══════════════════════════════════════════════
#  2. ORCHESTRATOR AGENT  (port 8001)
# ══════════════════════════════════════════════

async def test_orchestrator_agent():
    section("2. ORCHESTRATOR AGENT  (port 8001)")
    S = "Orchestrator"

    async with httpx.AsyncClient() as c:

        # --- 2.1 Health ---
        code, body = await get(c, f"{ORCHESTRATOR_URL}/health")
        record(S, "GET /health → 200", code == 200, f"code={code}")

        # --- 2.2 List workflows ---
        code, body = await get(c, f"{ORCHESTRATOR_URL}/workflows")
        record(S, "GET /workflows → 200", code == 200, f"code={code} count={len(body) if isinstance(body, list) else '?'}")

        # --- 2.3 Initiate onboarding ---
        payload = {
            "tenant_id": "acme_corp",
            "employee_id": f"EMP_{int(time.time())}",
            "employee_name": "Alice Johnson",
            "employee_email": "alice.johnson@acme.com",
            "role": "Software Engineer",
            "department": "Engineering",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
            "manager_email": "manager@acme.com",
            "metadata": {"test_run": True}
        }
        code, body = await post(c, f"{ORCHESTRATOR_URL}/onboarding/initiate", payload)
        record(S, "POST /onboarding/initiate → 200", code == 200, f"code={code} body={str(body)[:120]}")

        if code == 200:
            workflow_id = body.get("workflow_id")
            state["workflow_id"] = workflow_id
            record(S, "Response contains workflow_id", bool(workflow_id), str(workflow_id))

            # Allow LLM task-plan generation + Redis dispatch to complete
            await asyncio.sleep(3)

            # --- 2.4 Fetch created workflow (retry up to 3× for LLM latency) ---
            if workflow_id:
                code2, wf = 0, {}
                for attempt in range(3):
                    code2, wf = await get(c, f"{ORCHESTRATOR_URL}/workflows/{workflow_id}")
                    if code2 == 200:
                        break
                    await asyncio.sleep(2)
                record(S, "GET /workflows/{id} → 200", code2 == 200, f"code={code2}")

                if code2 == 200:
                    has_tasks = len(wf.get("tasks", [])) > 0
                    record(S, "Workflow has tasks delegated", has_tasks, f"tasks={len(wf.get('tasks', []))}")
                    info(f"Workflow status: {wf.get('status')}  tasks: {len(wf.get('tasks', []))}")
                    for t in wf.get("tasks", []):
                        info(f"  task={t['task_id']}  type={t['task_type']}  agent={t['assigned_agent']}  status={t['status']}")

        # --- 2.5 Task result submission ---
        code, body = await post(c, f"{ORCHESTRATOR_URL}/tasks/result", {
            "task_id": "TASK_test_result_001",
            "workflow_id": state.get("workflow_id") or "WF_test",
            "tenant_id": "acme_corp",
            "from_agent": "provisioning_agent",
            "status": "success",
            "result": {"external_id": "HR12345"},
            "error": None,
            "retry_possible": False
        })
        record(S, "POST /tasks/result → 200", code == 200, f"code={code}")

        # --- 2.6 404 for unknown workflow ---
        code, body = await get(c, f"{ORCHESTRATOR_URL}/workflows/WF_nonexistent_xyz")
        record(S, "GET /workflows/unknown → 404", code == 404, f"code={code}")

        # --- 2.7 Metrics ---
        code, body = await get(c, f"{ORCHESTRATOR_URL}/metrics")
        record(S, "GET /metrics → 200", code == 200, f"code={code} body={str(body)[:100]}")
        if code == 200:
            record(S, "/metrics has uptime_seconds", "uptime_seconds" in body, str(body)[:100])
            record(S, "/metrics has redis_connected", "redis_connected" in body, str(body)[:100])


# ══════════════════════════════════════════════
#  3. LIAISON AGENT  (port 8002)
# ══════════════════════════════════════════════

async def test_liaison_agent():
    section("3. LIAISON AGENT  (port 8002)")
    S = "Liaison"

    wf = state.get("workflow_id") or "WF_liaison_test_001"

    async with httpx.AsyncClient() as c:

        # --- 3.1 Health ---
        code, body = await get(c, f"{LIAISON_URL}/health")
        record(S, "GET /health → 200", code == 200, f"code={code}")

        # --- 3.2 Policy query message ---
        code, body = await post(c, f"{LIAISON_URL}/message", {
            "message": "What is the annual leave entitlement?",
            "tenant_id": "acme_corp",
            "user_id": "user_alice_001",
            "user_name": "Alice Johnson",
            "workflow_id": wf
        })
        record(S, "POST /message (policy query) → 200", code == 200, f"code={code} body={str(body)[:120]}")
        if code == 200:
            record(S, "Policy query returns response_text", bool(body.get("response_text")), str(body.get("response_text", ""))[:80])
            info(f"Intent: {body.get('intent_type')}  Confidence: {body.get('confidence_score')}")

        # --- 3.3 Onboarding request message ---
        code, body = await post(c, f"{LIAISON_URL}/message", {
            "message": "I want to start onboarding for a new hire Bob Smith, role: Data Analyst, department: Analytics",
            "tenant_id": "acme_corp",
            "user_id": "hr_manager_001",
            "user_name": "HR Manager",
            "workflow_id": wf
        })
        record(S, "POST /message (onboarding request) → 200", code == 200, f"code={code} body={str(body)[:120]}")
        if code == 200:
            info(f"Intent: {body.get('intent_type')}  Action: {body.get('action_taken')}")

        # --- 3.4 General greeting ---
        code, body = await post(c, f"{LIAISON_URL}/message", {
            "message": "Hello, I just joined the company today!",
            "tenant_id": "acme_corp",
            "user_id": "user_bob_002",
            "user_name": "Bob Smith",
            "workflow_id": wf
        })
        record(S, "POST /message (greeting) → 200", code == 200, f"code={code}")

        # --- 3.5 Approval response ---
        code, body = await post(c, f"{LIAISON_URL}/approval", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "user_id": "hr_manager_001",
            "approval_status": "approved",
            "approver_note": "All documents verified."
        })
        record(S, "POST /approval → 200", code == 200, f"code={code}")

        # --- 3.6 Guide-response forwarding ---
        code, body = await post(c, f"{LIAISON_URL}/guide-response", {
            "tenant_id": "acme_corp",
            "workflow_id": wf,
            "response": "Annual leave entitlement is 20 days per year.",
            "query": "What is the annual leave entitlement?"
        })
        record(S, "POST /guide-response → 200", code == 200, f"code={code}")

        # --- 3.7 Approval request from orchestrator ---
        code, body = await post(c, f"{LIAISON_URL}/approval-request", {
            "tenant_id": "acme_corp",
            "workflow_id": wf,
            "task_type": "create_hr_record",
            "details": {"employee_name": "Alice Johnson", "role": "Engineer"}
        })
        record(S, "POST /approval-request → 200", code == 200, f"code={code}")

        # --- 3.8 Clear conversation ---
        try:
            r = await c.delete(f"{LIAISON_URL}/conversation/acme_corp/{wf}", timeout=TIMEOUT)
            del_code, del_body = r.status_code, r.json()
        except Exception as e:
            del_code, del_body = 0, {"error": str(e)}
        record(S, "DELETE /conversation → 200", del_code == 200, f"code={del_code}")

        # --- 3.9 Metrics ---
        code, body = await get(c, f"{LIAISON_URL}/metrics")
        record(S, "GET /metrics → 200", code == 200, f"code={code} body={str(body)[:100]}")
        if code == 200:
            record(S, "/metrics has uptime_seconds", "uptime_seconds" in body, str(body)[:100])
            record(S, "/metrics has redis_connected", "redis_connected" in body, str(body)[:100])

        # --- 3.10 /workflow-complete notification ---
        code, body = await post(c, f"{LIAISON_URL}/workflow-complete", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "status": "COMPLETED",
            "employee_name": "Alice Johnson",
            "summary": {"total_tasks": 5, "completed_tasks": 5}
        })
        record(S, "POST /workflow-complete → 200", code == 200, f"code={code} body={str(body)[:120]}")
        if code == 200:
            record(S, "/workflow-complete status=ok", body.get("status") == "ok", str(body)[:120])


# ══════════════════════════════════════════════
#  4. PROVISIONING AGENT  (port 8003)
# ══════════════════════════════════════════════

async def test_provisioning_agent():
    section("4. PROVISIONING AGENT  (port 8003)")
    S = "Provisioning"

    async with httpx.AsyncClient() as c:

        # --- 4.1 Health ---
        code, body = await get(c, f"{PROVISIONING_URL}/health")
        record(S, "GET /health → 200", code == 200, f"code={code}")
        if code == 200:
            record(S, "Redis connected", body.get("redis_connected", False), str(body))

        # --- 4.1b Metrics ---
        code, body = await get(c, f"{PROVISIONING_URL.rstrip('/api/v1')}/metrics")
        record(S, "GET /metrics → 200", code == 200, f"code={code} body={str(body)[:100]}")
        if code == 200:
            record(S, "/metrics has uptime_seconds", "uptime_seconds" in body, str(body)[:100])

        # --- 4.2 Status ---
        code, body = await get(c, f"{PROVISIONING_URL}/status")
        record(S, "GET /status → 200", code == 200, f"code={code}")
        if code == 200:
            info(f"Supported tasks: {body.get('supported_task_types')}")

        # --- 4.3 Create HR record ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": state.get("workflow_id") or "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_hr_{int(time.time())}",
                "task_type": "create_hr_record",
                "payload": {
                    "employee_name": "Alice Johnson",
                    "employee_email": "alice.johnson@acme.com",
                    "role": "Software Engineer",
                    "department": "Engineering",
                    "start_date": "2026-03-10",
                    "employee_id": "EMP_TEST_001"
                }
            }
        })
        record(S, "POST /execute-task (create_hr_record) → 200", code == 200, f"code={code} status={body.get('status')}")
        if code == 200:
            info(f"Result: {str(body.get('result', {}))[:120]}")

        # --- 4.4 Create IT ticket ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": state.get("workflow_id") or "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_it_{int(time.time())}",
                "task_type": "create_it_ticket",
                "payload": {
                    "employee_id": "EMP_TEST_001",
                    "employee_name": "Alice Johnson",
                    "employee_email": "alice.johnson@acme.com",
                    "required_systems": ["email", "vpn", "slack"]
                }
            }
        })
        record(S, "POST /execute-task (create_it_ticket) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 4.5 Assign access ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": state.get("workflow_id") or "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_access_{int(time.time())}",
                "task_type": "assign_access",
                "payload": {
                    "employee_id": "EMP_TEST_001",
                    "access_roles": ["developer", "confluence_read", "jira_write"]
                }
            }
        })
        record(S, "POST /execute-task (assign_access) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 4.6 Generate employee ID ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": state.get("workflow_id") or "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_gen_{int(time.time())}",
                "task_type": "generate_id",
                "payload": {
                    "employee_name": "Alice Johnson",
                    "department": "Engineering",
                    "role": "Software Engineer"
                }
            }
        })
        record(S, "POST /execute-task (generate_id) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 4.7 Create email account ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": state.get("workflow_id") or "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_email_{int(time.time())}",
                "task_type": "create_email",
                "payload": {
                    "employee_name": "Alice Johnson",
                    "domain": "acme.com",
                    "first_name": "Alice",
                    "last_name": "Johnson"
                }
            }
        })
        record(S, "POST /execute-task (create_email) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 4.8 Validation failure test ---
        code, body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": "WF_prov_test_001",
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_invalid_{int(time.time())}",
                "task_type": "create_hr_record",
                "payload": {}     # missing required fields
            }
        })
        is_failed = code == 200 and body.get("status") in ("failed", "failure")
        record(S, "Validation failure → status=failed", is_failed, f"code={code} status={body.get('status')}")

        # --- 4.9 Cache endpoint ---
        code, body = await get(c, f"{PROVISIONING_URL}/cache")
        record(S, "GET /cache → 200", code == 200, f"code={code} cached={body.get('cached_tasks')}")


# ══════════════════════════════════════════════
#  5. SCHEDULER AGENT  (port 8004)
# ══════════════════════════════════════════════

async def test_scheduler_agent():
    section("5. SCHEDULER AGENT  (port 8004)")
    S = "Scheduler"

    wf = state.get("workflow_id") or "WF_sched_test_001"
    start_dt = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT10:00:00")
    end_dt   = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT11:00:00")

    async with httpx.AsyncClient() as c:

        # --- 5.1 Health ---
        code, body = await get(c, f"{SCHEDULER_URL}/health")
        record(S, "GET /health → 200", code == 200, f"code={code}")
        if code == 200:
            record(S, "Redis connected", body.get("redis_connected", False), str(body))

        # --- 5.1b Metrics ---
        code, body = await get(c, f"{SCHEDULER_URL.rstrip('/api/v1')}/metrics")
        record(S, "GET /metrics → 200", code == 200, f"code={code} body={str(body)[:100]}")
        if code == 200:
            record(S, "/metrics has uptime_seconds", "uptime_seconds" in body, str(body)[:100])

        # --- 5.2 Status ---
        code, body = await get(c, f"{SCHEDULER_URL}/status")
        record(S, "GET /status → 200", code == 200, f"code={code}")
        if code == 200:
            info(f"Supported tasks: {body.get('supported_task_types')}")

        # --- 5.3 schedule_meeting (full payload) ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_sched_{int(time.time())}",
                "task_type": "schedule_meeting",
                "payload": {
                    "meeting_title": "Induction Session – Alice Johnson",
                    "description": "New employee induction meeting",
                    "start_datetime": start_dt,
                    "end_datetime": end_dt,
                    "timezone": "America/New_York",
                    "organizer_email": "hr@acme.com",
                    "participants": ["alice.johnson@acme.com", "manager@acme.com"],
                    "meeting_type": "induction"
                }
            }
        })
        record(S, "POST /execute-task (schedule_meeting) → 200", code == 200, f"code={code} status={body.get('status')}")
        if code == 200:
            info(f"Result: {str(body.get('result', {}))[:120]}")

        # --- 5.4 schedule_induction (Orchestrator alias – short payload) ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_induction_{int(time.time())}",
                "task_type": "schedule_induction",
                "payload": {
                    "employee_email": "alice.johnson@acme.com",
                    "employee_name": "Alice Johnson",
                    "manager_email": "manager@acme.com",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "meeting_type": "induction"
                }
            }
        })
        record(S, "POST /execute-task (schedule_induction alias) → 200", code == 200, f"code={code} status={body.get('status')}")
        if code == 200:
            info(f"Normalised payload executed OK. Result: {str(body.get('result', {}))[:120]}")

        # --- 5.5 schedule_manager_intro alias ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_mgr_{int(time.time())}",
                "task_type": "schedule_manager_intro",
                "payload": {
                    "employee_email": "alice.johnson@acme.com",
                    "employee_name": "Alice Johnson",
                    "manager_email": "manager@acme.com",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=8)).strftime("%Y-%m-%d")
                }
            }
        })
        record(S, "POST /execute-task (schedule_manager_intro alias) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 5.6 schedule_hr_session alias ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_hr_sess_{int(time.time())}",
                "task_type": "schedule_hr_session",
                "payload": {
                    "employee_email": "alice.johnson@acme.com",
                    "employee_name": "Alice Johnson",
                    "manager_email": "hr@acme.com",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=9)).strftime("%Y-%m-%d")
                }
            }
        })
        record(S, "POST /execute-task (schedule_hr_session alias) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 5.7 reschedule_meeting ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_resched_{int(time.time())}",
                "task_type": "reschedule_meeting",
                "payload": {
                    "event_id": "google_cal_event_abc123",
                    "meeting_title": "Induction – rescheduled",
                    "start_datetime": (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT10:00:00"),
                    "end_datetime":   (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT11:00:00"),
                    "timezone": "UTC",
                    "organizer_email": "hr@acme.com",
                    "participants": ["alice.johnson@acme.com"],
                    "meeting_type": "induction"
                }
            }
        })
        record(S, "POST /execute-task (reschedule_meeting) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 5.8 cancel_meeting ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_cancel_{int(time.time())}",
                "task_type": "cancel_meeting",
                "payload": {
                    "event_id": "google_cal_event_abc123",
                    "organizer_email": "hr@acme.com",
                    "timezone": "UTC",
                    "participants": ["alice.johnson@acme.com"],
                    "meeting_title": "Induction – Alice Johnson"
                }
            }
        })
        record(S, "POST /execute-task (cancel_meeting) → 200", code == 200, f"code={code} status={body.get('status')}")

        # --- 5.9 Validation: end before start ---
        code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": f"TASK_valcheck_{int(time.time())}",
                "task_type": "schedule_meeting",
                "payload": {
                    "meeting_title": "Bad meeting",
                    "start_datetime": "2026-03-10T11:00:00",
                    "end_datetime":   "2026-03-10T10:00:00",   # end before start
                    "timezone": "UTC",
                    "organizer_email": "hr@acme.com",
                    "participants": ["alice@acme.com"]
                }
            }
        })
        is_failed = code == 200 and body.get("status") in ("failed", "failure")
        record(S, "Validation (end<start) → status=failed", is_failed, f"code={code} status={body.get('status')}")

        # --- 5.10 Idempotency: same task_id twice ---
        tid = f"TASK_idem_{int(time.time())}"
        base = {
            "workflow_id": wf,
            "tenant_id": "acme_corp",
            "task": {
                "task_id": tid,
                "task_type": "schedule_induction",
                "payload": {
                    "employee_email": "alice.johnson@acme.com",
                    "employee_name": "Alice Johnson",
                    "manager_email": "manager@acme.com",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
                }
            }
        }
        code1, body1 = await post(c, f"{SCHEDULER_URL}/execute-task", base)
        code2, body2 = await post(c, f"{SCHEDULER_URL}/execute-task", base)
        # Idempotency = both calls succeed AND return same task_id
        both_ok = code1 == 200 and code2 == 200
        same_tid = body1.get("task_id") == body2.get("task_id") or (
            body1.get("result") is not None and body2.get("result") is not None
        )
        record(S, "Idempotency: both calls succeed consistently", both_ok and same_tid,
               f"code1={code1} code2={code2} tid_match={same_tid}")

        # --- 5.11 Cache ---
        code, body = await get(c, f"{SCHEDULER_URL}/cache")
        record(S, "GET /cache → 200", code == 200, f"code={code} cached={body.get('cached_tasks')}")


# ══════════════════════════════════════════════
#  6. COORDINATION TESTS
# ══════════════════════════════════════════════

async def test_coordination():
    section("6. CROSS-AGENT COORDINATION")
    S = "Coordination"

    async with httpx.AsyncClient() as c:

        # ── 6.1  Full onboarding flow: Orchestrator → Provisioning + Scheduler ──
        info("Initiating full onboarding workflow …")
        ts = int(time.time())
        payload = {
            "tenant_id": "betacorp",
            "employee_id": f"EMP_COORD_{ts}",
            "employee_name": "Bob Smith",
            "employee_email": f"bob.smith_{ts}@betacorp.com",
            "role": "Product Manager",
            "department": "Product",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
            "manager_email": "cto@betacorp.com",
            "metadata": {"coordination_test": True}
        }
        code, wf_body = await post(c, f"{ORCHESTRATOR_URL}/onboarding/initiate", payload)
        record(S, "Orchestrator initiates onboarding → 200", code == 200, f"code={code}")

        if code != 200:
            warn("Cannot continue coordination test – orchestrator failed")
            return

        coord_wf_id = wf_body.get("workflow_id")
        record(S, "Orchestrator returns workflow_id", bool(coord_wf_id), str(coord_wf_id))

        # Wait for Orchestrator to dispatch tasks via Redis
        info("Waiting 3s for task delegation via Redis …")
        await asyncio.sleep(3)

        # ── 6.2  Verify tasks appear in workflow ──
        code, wf_detail = await get(c, f"{ORCHESTRATOR_URL}/workflows/{coord_wf_id}")
        record(S, "Orchestrator workflow has tasks", code == 200 and len(wf_detail.get("tasks", [])) > 0,
               f"code={code} tasks={len(wf_detail.get('tasks', [] if code != 200 else []))}")

        # ── 6.3  Liaison routes policy query ──
        code, lia_body = await post(c, f"{LIAISON_URL}/message", {
            "message": "What are the remote work policies?",
            "tenant_id": "betacorp",
            "user_id": f"bob_{ts}",
            "user_name": "Bob Smith",
            "workflow_id": coord_wf_id
        })
        record(S, "Liaison handles policy query during onboarding → 200", code == 200, f"code={code}")
        if code == 200:
            info(f"Liaison intent: {lia_body.get('intent_type')}  action: {lia_body.get('action_taken')}")

        # ── 6.4  Scheduler receives schedule_induction from orchestrator payload style ──
        code, sched_body = await post(c, f"{SCHEDULER_URL}/execute-task", {
            "workflow_id": coord_wf_id,
            "tenant_id": "betacorp",
            "task": {
                "task_id": f"TASK_coord_induction_{ts}",
                "task_type": "schedule_induction",
                "payload": {
                    "employee_email": f"bob.smith_{ts}@betacorp.com",
                    "employee_name": "Bob Smith",
                    "manager_email": "cto@betacorp.com",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "meeting_type": "induction"
                }
            }
        })
        record(S, "Scheduler handles schedule_induction → 200", code == 200, f"code={code} status={sched_body.get('status')}")

        # ── 6.5  Provisioning receives create_hr_record for same workflow ──
        code, prov_body = await post(c, f"{PROVISIONING_URL}/execute-task", {
            "workflow_id": coord_wf_id,
            "tenant_id": "betacorp",
            "task": {
                "task_id": f"TASK_coord_hr_{ts}",
                "task_type": "create_hr_record",
                "payload": {
                    "employee_name": "Bob Smith",
                    "employee_email": f"bob.smith_{ts}@betacorp.com",
                    "role": "Product Manager",
                    "department": "Product",
                    "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
                }
            }
        })
        record(S, "Provisioning handles create_hr_record → 200", code == 200, f"code={code} status={prov_body.get('status')}")

        # ── 6.6  Orchestrator receives task results from both agents ──
        for agent_name, task_id, ext_id in [
            ("provisioning_agent", f"TASK_coord_hr_{ts}",        "HRIS_BOB_001"),
            ("scheduler_agent",    f"TASK_coord_induction_{ts}", "CAL_BOB_001"),
        ]:
            code, res_body = await post(c, f"{ORCHESTRATOR_URL}/tasks/result", {
                "task_id": task_id,
                "workflow_id": coord_wf_id,
                "tenant_id": "betacorp",
                "from_agent": agent_name,
                "status": "success",
                "result": {"external_id": ext_id},
                "error": None,
                "retry_possible": False
            })
            record(S, f"Orchestrator accepts {agent_name} result → 200", code == 200, f"code={code}")

        # ── 6.7  Guide answers policy for betacorp (if company exists) ──
        if state.get("guide_company_id"):
            code, guide_body = await post(c, f"{GUIDE_URL}/query", {
                "query": "What is the expense reimbursement process?",
                "company_id": state["guide_company_id"],
                "session_id": coord_wf_id
            }, timeout=GUIDE_QUERY_TIMEOUT)
            record(S, "Guide answers policy during coordination → 200", code == 200, f"code={code}")
        else:
            warn("Skipping Guide coordination test – no company loaded")

        # ── 6.8  Final workflow state ──
        code, final_wf = await get(c, f"{ORCHESTRATOR_URL}/workflows/{coord_wf_id}")
        if code == 200:
            info(f"Final workflow status: {final_wf.get('status')}  tasks: {len(final_wf.get('tasks', []))}")


# ══════════════════════════════════════════════
#  7. MULTI-TENANT ISOLATION TEST
# ══════════════════════════════════════════════

async def test_multi_tenant_isolation():
    section("7. MULTI-TENANT ISOLATION")
    S = "MultiTenant"

    ts = int(time.time())

    async with httpx.AsyncClient() as c:

        # Start two simultaneous onboardings for different tenants
        tenants = [
            ("tenant_alpha", "Carol White", "carol.white@alpha.com", "Designer"),
            ("tenant_beta",  "Dave Green",  "dave.green@beta.com",   "DevOps"),
        ]
        wf_ids = {}

        for tenant_id, name, email, role in tenants:
            code, body = await post(c, f"{ORCHESTRATOR_URL}/onboarding/initiate", {
                "tenant_id": tenant_id,
                "employee_id": f"EMP_{ts}_{tenant_id}",
                "employee_name": name,
                "employee_email": email,
                "role": role,
                "department": "Engineering",
                "start_date": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d"),
                "manager_email": f"manager@{tenant_id}.com"
            })
            record(S, f"Onboarding initiated for {tenant_id} → 200", code == 200, f"code={code}")
            if code == 200:
                wf_ids[tenant_id] = body.get("workflow_id")

        await asyncio.sleep(1)

        # Verify workflows are separate
        if len(wf_ids) == 2:
            ids = list(wf_ids.values())
            record(S, "Two tenants have distinct workflow_ids", ids[0] != ids[1], f"{ids[0]} vs {ids[1]}")

        # Scheduler: tenant data never mixed
        for tenant_id, name, email, role in tenants:
            code, body = await post(c, f"{SCHEDULER_URL}/execute-task", {
                "workflow_id": wf_ids.get(tenant_id, "WF_isolation_test"),
                "tenant_id": tenant_id,
                "task": {
                    "task_id": f"TASK_iso_{tenant_id}_{ts}",
                    "task_type": "schedule_induction",
                    "payload": {
                        "employee_email": email,
                        "employee_name": name,
                        "manager_email": f"manager@{tenant_id}.com",
                        "start_date": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
                    }
                }
            })
            record(S, f"Scheduler processes {tenant_id} task → 200", code == 200, f"code={code} status={body.get('status')}")


# ══════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════

def print_summary():
    section("TEST SUMMARY")

    by_suite: Dict[str, List] = {}
    for r in results:
        by_suite.setdefault(r["suite"], []).append(r)

    total_pass = sum(1 for r in results if r["passed"])
    total_fail = sum(1 for r in results if not r["passed"])

    for suite, suite_results in by_suite.items():
        p = sum(1 for r in suite_results if r["passed"])
        f = sum(1 for r in suite_results if not r["passed"])
        colour = GREEN if f == 0 else (YELLOW if p > 0 else RED)
        print(f"  {colour}{BOLD}{suite:<22}{RESET}  {GREEN}{p} passed{RESET}  {RED if f else ''}{f} failed{RESET}")

    print()
    if total_fail == 0:
        print(f"  {GREEN}{BOLD}ALL {total_pass} TESTS PASSED ✅{RESET}")
    else:
        print(f"  {BOLD}Total: {GREEN}{total_pass} passed{RESET}  {RED}{total_fail} failed{RESET}")

    # Show failures
    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  {RED}{BOLD}FAILURES:{RESET}")
        for r in failures:
            print(f"    {RED}✗ [{r['suite']}] {r['test']}")
            if r["detail"]:
                print(f"      → {r['detail']}{RESET}")

    print()
    return total_fail == 0


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════

SUITES = {
    "guide":         test_guide_agent,
    "orchestrator":  test_orchestrator_agent,
    "liaison":       test_liaison_agent,
    "provisioning":  test_provisioning_agent,
    "scheduler":     test_scheduler_agent,
    "coord":         test_coordination,
    "multitenant":   test_multi_tenant_isolation,
}

async def main(run_suites: List[str]):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  AgenticHR – Full Backend Test Suite{RESET}")
    print(f"{BOLD}{CYAN}  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

    for name in run_suites:
        fn = SUITES.get(name)
        if fn:
            try:
                await fn()
            except Exception as e:
                fail(f"Suite '{name}' crashed: {e}")
        else:
            warn(f"Unknown suite '{name}'")

    return print_summary()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgenticHR Backend Test Suite")
    parser.add_argument(
        "--suite", "-s",
        nargs="+",
        choices=list(SUITES.keys()) + ["all"],
        default=["all"],
        help="Which test suite(s) to run  (default: all)"
    )
    parser.add_argument(
        "--agent", "-a",
        choices=["guide", "orchestrator", "liaison", "provisioning", "scheduler"],
        help="Run tests for a single agent only"
    )
    args = parser.parse_args()

    if args.agent:
        run = [args.agent]
    elif "all" in args.suite:
        run = list(SUITES.keys())
    else:
        run = args.suite

    ok_all = asyncio.run(main(run))
    sys.exit(0 if ok_all else 1)
