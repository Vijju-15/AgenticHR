"""Core Orchestrator Agent logic using Groq LLM."""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import uuid
from datetime import datetime, timezone
import httpx

from src.config.settings import settings
from src.services.email_service import send_meeting_invite
from src.schemas.mcp_message import (
    MCPMessage, TaskPayload, DelegateTask, AgentType, 
    MessageType, WorkflowState, OnboardingInitiation, TaskResult
)
from src.schemas.workflow import Workflow, WorkflowTask, WorkflowStatus, TaskStatus
from src.database.db import get_db
from src.models.workflow_model import workflow_to_dict, task_to_dict
from src.messaging.redis_client import redis_client


class OrchestratorAgent:
    """
    Orchestrator Agent - Central workflow planning and task delegation.
    
    This agent:
    - Receives onboarding initiation requests
    - Breaks workflows into structured tasks
    - Delegates tasks to specialized agents
    - Maintains workflow state
    - Handles approvals and retries
    """
    
    def __init__(self):
        """Initialize Orchestrator Agent."""
        self.model = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )
        self.agent_type = AgentType.ORCHESTRATOR
        logger.info(f"Orchestrator Agent initialized with Groq model: {settings.groq_model}")
        
        self.system_prompt = """You are the Orchestrator Agent in a distributed multi-agent onboarding system called "AgenticHR".

You are NOT a chatbot.
You are a workflow planner, task decomposer, and delegation controller.

RESPONSIBILITIES:
1. Receive onboarding initiation requests
2. Break the onboarding process into structured tasks
3. Delegate tasks to appropriate agents
4. Maintain workflow state
5. Handle approval logic
6. Retry or escalate failed tasks
7. Track completion status
8. Ensure idempotency

AGENT CAPABILITIES:
- Liaison Agent: Handles conversation, detects intent, routes queries. Also handles leave-request routing, onboarding-journey queries, and HR-action routing.
- Guide Agent: Answers HR policy questions (RAG-based), processes leave requests autonomously, guides onboarding step completion.
- Employee Setup Agent (provisioning_agent): Creates employee records in HRIS, generates unique employee IDs, assigns departments and roles, sends welcome-credential emails, initializes structured onboarding journeys, creates Day-1/2/3 onboarding checklists.
- Scheduler Agent: Schedules meetings, sends Google Calendar invites, creates Google Meet links.

SUPPORTED TASK TYPES for Employee Setup Agent:
  create_employee_record   – Register employee in HRIS
  generate_employee_id     – Generate formatted employee ID (DEPT-YYYY-XXXX)
  assign_department        – Assign department, role, and reporting manager
  send_welcome_credentials – Email temporary login credentials to new hire
  initialize_onboarding    – Create structured 3-day onboarding journey in DB
  create_onboarding_checklist – Build Day-1/2/3 task checklist

WORKFLOW STAGES:
CREATED → INITIATED → PROVISIONING_PENDING → SCHEDULING_PENDING → WAITING_APPROVAL (if needed) → ACTIVE → COMPLETED / FAILED

COMMUNICATION:
You must output ONLY valid JSON in this format:
{
  "action": "delegate_task" | "update_state" | "complete_workflow" | "retry_task" | "escalate",
  "workflow_id": "string",
  "tenant_id": "string",
  "target_agent": "provisioning_agent | scheduler_agent | liaison_agent",
  "task": {
      "task_id": "unique_id",
      "task_type": "string",
      "payload": {}
  },
  "new_state": "workflow_state",
  "reason": "explanation"
}

RULES:
- Never execute external tools directly
- Only delegate to other agents
- No duplicate tasks
- Always include tenant_id
- Think step-by-step internally, output only final JSON
- No markdown, no explanations, ONLY JSON"""
    
    def initiate_onboarding(self, request: OnboardingInitiation) -> Workflow:
        """
        Initiate new onboarding workflow.
        
        Args:
            request: Onboarding initiation request
            
        Returns:
            Created workflow
        """
        workflow_id = f"WF_{request.tenant_id}_{request.employee_id}_{uuid.uuid4().hex[:8]}"
        
        # Create workflow in database
        workflow = Workflow(
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            employee_id=request.employee_id,
            employee_name=request.employee_name,
            employee_email=request.employee_email,
            role=request.role,
            department=request.department,
            start_date=request.start_date,
            manager_id=request.manager_id,
            manager_email=request.manager_email,
            status=WorkflowStatus.CREATED,
            metadata=request.metadata
        )
        
        try:
            with get_db() as db:
                # Convert Pydantic model to MongoDB document
                workflow_doc = workflow_to_dict(
                    workflow_id=workflow.workflow_id,
                    tenant_id=workflow.tenant_id,
                    employee_id=workflow.employee_id,
                    employee_name=workflow.employee_name,
                    employee_email=workflow.employee_email,
                    role=workflow.role,
                    department=workflow.department,
                    start_date=workflow.start_date,
                    manager_id=workflow.manager_id,
                    manager_email=workflow.manager_email,
                    status=WorkflowStatus.CREATED,
                    metadata=workflow.metadata or {}
                )
                db.workflows.insert_one(workflow_doc)
                logger.info(f"Created workflow {workflow_id} for tenant {workflow.tenant_id}")
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            raise
        
        # Use Gemini to decompose into tasks
        self._plan_and_delegate_tasks(workflow)
        
        return workflow
    
    def _plan_and_delegate_tasks(self, workflow: Workflow):
        """
        Use Gemini to plan and delegate tasks.
        
        Args:
            workflow: Workflow to plan tasks for
        """
        prompt = f"""
Onboarding workflow initiated:
- Workflow ID: {workflow.workflow_id}
- Tenant: {workflow.tenant_id}
- Employee: {workflow.employee_name} ({workflow.employee_id})
- Email: {workflow.employee_email}
- Role: {workflow.role}
- Department: {workflow.department}
- Start Date: {workflow.start_date}
- Manager: {workflow.manager_email}

Plan the onboarding tasks and delegate them. Output a JSON array of delegation actions:

For onboarding, you MUST delegate these tasks in order:
1. generate_employee_id       → provisioning_agent   (generate formatted employee ID)
2. create_employee_record     → provisioning_agent   (register in HRIS with generated ID)
3. assign_department          → provisioning_agent   (assign department and manager)
4. send_welcome_credentials   → provisioning_agent   (email temp credentials)
5. initialize_onboarding      → provisioning_agent   (create 3-day onboarding journey)
6. schedule_induction_meeting → scheduler_agent      (Day-1 induction with manager)
7. initiate_welcome_conversation → liaison_agent     (send welcome message to new hire)

Output ONLY a JSON array of DelegateTask objects. No markdown, no explanations.
"""
        
        try:
            response = self.model.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ])
            response_text = response.content.strip()
            
            # Clean JSON from markdown
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Parse delegation tasks
            try:
                delegate_actions = json.loads(response_text)
                if not isinstance(delegate_actions, list):
                    delegate_actions = [delegate_actions]
            except json.JSONDecodeError:
                # Fallback to default task plan
                logger.warning("Failed to parse Gemini response, using default task plan")
                delegate_actions = self._get_default_task_plan(workflow)

            # Guardrail: ensure critical provisioning tasks are present.
            required_task_types = {
                "create_employee_record",
                "send_welcome_credentials",
                "initialize_onboarding",
            }
            planned_types = {
                (a.get("task") or {}).get("task_type")
                for a in delegate_actions
                if isinstance(a, dict)
            }
            if not required_task_types.issubset(planned_types):
                logger.warning(
                    "LLM plan missing required provisioning tasks ({}). Using deterministic default plan.",
                    ", ".join(sorted(required_task_types - planned_types)),
                )
                delegate_actions = self._get_default_task_plan(workflow)
            
            # Execute delegations
            for action_data in delegate_actions:
                self._execute_delegation(action_data, workflow)
            
            # Update workflow state
            self._update_workflow_state(workflow.workflow_id, WorkflowStatus.INITIATED)
            
        except Exception as e:
            logger.error(f"Error planning tasks: {e}")
            # Fallback to default plan
            delegate_actions = self._get_default_task_plan(workflow)
            for action_data in delegate_actions:
                self._execute_delegation(action_data, workflow)
    
    def _get_default_task_plan(self, workflow: Workflow) -> List[Dict[str, Any]]:
        """Get default task plan as fallback — full pre-joining + onboarding sequence."""
        w = workflow  # shorthand

        def task(task_type, payload, agent="provisioning_agent", state="PROVISIONING_PENDING", reason=""):
            return {
                "action": "delegate_task",
                "workflow_id": w.workflow_id,
                "tenant_id":   w.tenant_id,
                "target_agent": agent,
                "task": {
                    "task_id":   f"TASK_{uuid.uuid4().hex[:8]}",
                    "task_type": task_type,
                    "payload":   payload,
                },
                "new_state": state,
                "reason":    reason or task_type,
            }

        base = {
            "employee_id":    w.employee_id,
            "employee_name":  w.employee_name,
            "employee_email": w.employee_email,
            "role":           getattr(w, "role", ""),
            "department":     getattr(w, "department", ""),
            "start_date":     getattr(w, "start_date", ""),
        }

        return [
            # ── 1. Create HRIS record ──────────────────────────────────────
            task(
                "create_employee_record",
                {**base, "joining_date": base["start_date"]},
                reason="Register new hire in HRIS",
            ),
            # ── 2. Generate Employee ID ────────────────────────────────────
            task(
                "generate_employee_id",
                base,
                reason="Generate unique employee ID",
            ),
            # ── 3. Send Offer Letter ───────────────────────────────────────
            task(
                "send_offer_letter",
                {
                    **base,
                    "workflow_id":      w.workflow_id,
                    "candidate_name":   w.employee_name,
                    "candidate_email":  w.employee_email,
                    "joining_date":     base["start_date"],
                    "stipend":          getattr(w, "stipend", "As per company norms"),
                    "acceptance_token": f"tok_{uuid.uuid4().hex}",
                },
                state="OFFER_SENT",
                reason="Send offer letter email to candidate",
            ),
            # ── 4. Assign Department ──────────────────────────────────────
            task(
                "assign_department",
                {**base, "manager_id": getattr(w, "manager_id", "")},
                reason="Assign department and reporting manager",
            ),
            # ── 5. Manager Introduction ────────────────────────────────────
            task(
                "send_manager_introduction",
                {
                    **base,
                    "candidate_name":  w.employee_name,
                    "candidate_email": w.employee_email,
                    "joining_date":    base["start_date"],
                    "manager_name":    getattr(w, "manager_name", "Your Manager"),
                    "manager_email":   getattr(w, "manager_email", ""),
                },
                state="MANAGER_ASSIGNED",
                reason="Introduce candidate to their manager via email",
            ),
            # ── 6. Send Welcome Credentials ────────────────────────────────
            task(
                "send_welcome_credentials",
                base,
                state="CREDENTIALS_SENT",
                reason="Email login credentials to the new hire",
            ),
            # ── 7. Initialize Onboarding Journey ──────────────────────────
            task(
                "initialize_onboarding",
                base,
                reason="Create structured onboarding profile and journey",
            ),
            # ── 8. Schedule Induction ──────────────────────────────────────
            task(
                "schedule_induction",
                {
                    "employee_email": w.employee_email,
                    "employee_name":  w.employee_name,
                    "manager_email":  getattr(w, "manager_email", ""),
                    "start_date":     base["start_date"],
                    "meeting_type":   "induction",
                },
                agent="scheduler_agent",
                state="SCHEDULING_PENDING",
                reason="Schedule Day-1 induction meeting",
            ),
            # ── 9. Activate Intern Conversation ───────────────────────────
            task(
                "initiate_conversation",
                {
                    "employee_id":    w.employee_id,
                    "employee_name":  w.employee_name,
                    "employee_email": w.employee_email,
                },
                agent="liaison_agent",
                state="ACTIVE",
                reason="Begin conversation with new hire via Liaison Agent",
            ),
        ]
    
    def _execute_delegation(self, action_data: Dict[str, Any], workflow: Workflow):
        """Execute delegation action."""
        try:
            action_data = self._normalize_delegate_action(action_data, workflow)

            # LLM can emit state-only actions; handle them without task insertion.
            if action_data.get("action") != "delegate_task":
                if action_data.get("action") == "update_state" and action_data.get("new_state"):
                    try:
                        self._update_workflow_state(
                            workflow.workflow_id,
                            WorkflowStatus(action_data["new_state"]),
                        )
                    except Exception as state_err:
                        logger.warning(f"Skipping invalid update_state action: {state_err}")
                return

            delegate_task = DelegateTask(**action_data)
            
            # Store task in database
            task_doc = task_to_dict(
                task_id=delegate_task.task.task_id,
                workflow_id=delegate_task.workflow_id,
                tenant_id=delegate_task.tenant_id,
                task_type=delegate_task.task.task_type,
                assigned_agent=delegate_task.target_agent.value,
                payload=delegate_task.task.payload,
                status=TaskStatus.PENDING,
                retry_count=0,
                max_retries=settings.max_task_retries
            )

            with get_db() as db:
                try:
                    db.tasks.insert_one(task_doc)
                except Exception as insert_err:
                    # Guardrail for duplicate task IDs from LLM plans
                    if "E11000" in str(insert_err):
                        new_task_id = f"TASK_{uuid.uuid4().hex[:10]}"
                        delegate_task.task.task_id = new_task_id
                        task_doc["task_id"] = new_task_id
                        db.tasks.insert_one(task_doc)
                        logger.warning(
                            "Duplicate task_id detected; regenerated task_id -> {}",
                            new_task_id,
                        )
                    else:
                        raise
            
            # Send MCP message via Redis
            mcp_message = MCPMessage(
                message_id=f"MSG_{uuid.uuid4().hex[:12]}",
                workflow_id=delegate_task.workflow_id,
                tenant_id=delegate_task.tenant_id,
                from_agent=self.agent_type,
                to_agent=delegate_task.target_agent,
                message_type=MessageType.TASK_REQUEST,
                task=delegate_task.task,
                data={"reason": delegate_task.reason},
                metadata=workflow.metadata
            )
            
            redis_client.publish_message(mcp_message)
            logger.info(f"Delegated task {delegate_task.task.task_id} to {delegate_task.target_agent.value}")
            
        except Exception as e:
            logger.error(f"Error executing delegation: {e}")

    def _normalize_delegate_action(self, action_data: Dict[str, Any], workflow: Workflow) -> Dict[str, Any]:
        """Normalize LLM delegate output to match strict schema and DB constraints."""
        if not isinstance(action_data, dict):
            return action_data

        normalized = dict(action_data)

        # Map legacy/new-state aliases emitted by prompt history.
        state_aliases = {
            "SETUP_PENDING": "PROVISIONING_PENDING",
            "JOURNEY_IN_PROGRESS": "PROVISIONING_PENDING",
            "ONBOARDING_IN_PROGRESS": "PROVISIONING_PENDING",
        }
        ns = normalized.get("new_state")
        if isinstance(ns, str):
            normalized["new_state"] = state_aliases.get(ns, ns)

        task = normalized.get("task")
        if isinstance(task, dict):
            task = dict(task)

            # Normalize alias task types emitted by prompt/LLM variants
            task_type_aliases = {
                "schedule_induction_meeting": "schedule_induction",
                "initiate_welcome_conversation": "initiate_conversation",
            }
            ttype = str(task.get("task_type") or "").strip()
            if ttype in task_type_aliases:
                task["task_type"] = task_type_aliases[ttype]

            # Ensure unique, non-generic task IDs.
            task_id = str(task.get("task_id") or "").strip()
            if (not task_id) or task_id.lower().startswith("task_"):
                task["task_id"] = f"TASK_{uuid.uuid4().hex[:10]}"

            # Keep payload stable
            if not isinstance(task.get("payload"), dict):
                task["payload"] = {}

            # Backfill required onboarding payload fields from workflow context.
            payload = dict(task.get("payload") or {})
            payload.setdefault("employee_id", workflow.employee_id)
            payload.setdefault("employee_name", workflow.employee_name)
            payload.setdefault("employee_email", workflow.employee_email)
            payload.setdefault("role", workflow.role)
            payload.setdefault("department", workflow.department)
            payload.setdefault("start_date", workflow.start_date)
            payload.setdefault("manager_id", workflow.manager_id)
            payload.setdefault("manager_email", workflow.manager_email)
            task["payload"] = payload

            normalized["task"] = task

        return normalized
    
    def handle_task_result(self, task_result: TaskResult):
        """
        Handle task completion result from agents.
        
        Args:
            task_result: Task result from agent
        """
        logger.info(f"Received task result for {task_result.task_id}: {task_result.status}")
        
        try:
            with get_db() as db:
                task_doc = db.tasks.find_one({"task_id": task_result.task_id})
                
                if not task_doc:
                    # HR-direct meeting scheduling (POST /meetings/schedule) writes
                    # the meeting to db.meetings with a task_id, but does NOT write
                    # a task to db.tasks.  Handle that case here.
                    result_data = task_result.result or {}
                    meet_link = result_data.get("meet_link") or result_data.get("hangoutLink", "")
                    event_id  = result_data.get("event_id") or result_data.get("id", "")
                    updated = db.meetings.update_one(
                        {"task_id": task_result.task_id},
                        {"$set": {
                            "meet_link":  meet_link,
                            "event_id":   event_id,
                            "status":     "scheduled" if meet_link else "pending",
                            "updated_at": datetime.now(timezone.utc),
                        }}
                    )
                    if updated.matched_count:
                        logger.info(
                            f"[fallback] Meeting updated via task_id={task_result.task_id} "
                            f"meet_link={meet_link}"
                        )
                        # Also send email if meet_link present
                        if meet_link and task_result.status == "success":
                            mtg = db.meetings.find_one(
                                {"task_id": task_result.task_id},
                                {"personal_email": 1, "intern_name": 1, "title": 1,
                                 "start_datetime": 1, "end_datetime": 1, "hr_email": 1, "_id": 0}
                            ) or {}
                            personal_email = mtg.get("personal_email", "")
                            if personal_email:
                                try:
                                    send_meeting_invite(
                                        personal_email=personal_email,
                                        intern_name=mtg.get("intern_name", "Intern"),
                                        meeting_title=mtg.get("title", "HR Meeting"),
                                        start_datetime=mtg.get("start_datetime", ""),
                                        end_datetime=mtg.get("end_datetime", ""),
                                        meet_link=meet_link,
                                        calendar_url=result_data.get("calendar_url", ""),
                                        hr_email=mtg.get("hr_email", ""),
                                    )
                                    logger.info(f"Meeting invite sent to {personal_email}")
                                except Exception as _e:
                                    logger.warning(f"Email invite failed: {_e}")
                    else:
                        logger.error(f"Task {task_result.task_id} not found in tasks or meetings")
                    return

                if task_result.status == "success":
                    db.tasks.update_one(
                        {"task_id": task_result.task_id},
                        {"$set": {
                            "status": TaskStatus.COMPLETED.value,
                            "result": task_result.result,
                            "completed_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    logger.info(f"Task {task_result.task_id} completed successfully")

                    # If this was a meeting-scheduling task, update the meetings collection
                    _MEETING_TASK_TYPES = {
                        "schedule_meeting", "schedule_induction",
                        "schedule_manager_intro", "schedule_hr_session",
                    }
                    if task_doc.get("task_type") in _MEETING_TASK_TYPES:
                        meeting_id = task_doc.get("payload", {}).get("meeting_id")
                        if meeting_id:
                            result_data = task_result.result or {}
                            meet_link = result_data.get("meet_link") or result_data.get("hangoutLink", "")
                            event_id  = result_data.get("event_id") or result_data.get("id", "")
                            db.meetings.update_one(
                                {"meeting_id": meeting_id},
                                {"$set": {
                                    "meet_link":  meet_link,
                                    "event_id":   event_id,
                                    "status":     "scheduled" if meet_link else "pending",
                                    "updated_at": datetime.now(timezone.utc),
                                }},
                            )
                            logger.info(f"Meeting {meeting_id} updated with meet_link after scheduler completion")
                            # Send email notification to intern's personal email
                            if meet_link:
                                meeting_doc = db.meetings.find_one(
                                    {"meeting_id": meeting_id},
                                    {"personal_email": 1, "intern_name": 1, "meeting_title": 1,
                                     "start_datetime": 1, "end_datetime": 1, "hr_email": 1, "_id": 0}
                                ) or {}
                                personal_email = meeting_doc.get("personal_email", "")
                                if personal_email:
                                    try:
                                        send_meeting_invite(
                                            personal_email=personal_email,
                                            intern_name=meeting_doc.get("intern_name", "Intern"),
                                            meeting_title=meeting_doc.get("meeting_title", "HR Meeting"),
                                            start_datetime=meeting_doc.get("start_datetime", ""),
                                            end_datetime=meeting_doc.get("end_datetime", ""),
                                            meet_link=meet_link,
                                            calendar_url=result_data.get("calendar_url", ""),
                                            hr_email=meeting_doc.get("hr_email", ""),
                                        )
                                        logger.info(f"Meeting invite email sent to {personal_email}")
                                    except Exception as _email_err:
                                        logger.warning(f"Failed to send meeting invite email: {_email_err}")
                    
                elif task_result.status == "failure":
                    if task_doc["retry_count"] < task_doc["max_retries"] and task_result.retry_possible:
                        db.tasks.update_one(
                            {"task_id": task_result.task_id},
                            {"$set": {
                                "status": TaskStatus.RETRYING.value,
                                "error": task_result.error,
                                "updated_at": datetime.now(timezone.utc)
                            },
                             "$inc": {"retry_count": 1}}
                        )
                        logger.info(f"Retrying task {task_result.task_id} (attempt {task_doc['retry_count'] + 1})")
                        # Re-delegate task
                        self._retry_task(task_doc)
                    else:
                        db.tasks.update_one(
                            {"task_id": task_result.task_id},
                            {"$set": {
                                "status": TaskStatus.FAILED.value,
                                "error": task_result.error,
                                "updated_at": datetime.now(timezone.utc)
                            }}
                        )
                        logger.error(f"Task {task_result.task_id} failed permanently")
                
                # Check if workflow is complete
                self._check_workflow_completion(task_result.workflow_id)
                
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
    
    def _retry_task(self, task_doc: Dict[str, Any]):
        """Retry failed task."""
        # Create retry delegation
        # Implementation similar to _execute_delegation
        pass
    
    def _update_workflow_state(self, workflow_id: str, new_state: WorkflowStatus):
        """Update workflow state."""
        try:
            with get_db() as db:
                db.workflows.update_one(
                    {"workflow_id": workflow_id},
                    {"$set": {
                        "status": new_state.value,
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                logger.info(f"Updated workflow {workflow_id} state to {new_state.value}")
        except Exception as e:
            logger.error(f"Error updating workflow state: {e}")

    def _notify_liaison(self, workflow_id: str, tenant_id: str, employee_name: str, status: str, tasks: list):
        """Fire-and-forget HTTP notification to Liaison Agent on workflow completion/failure."""
        try:
            completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED.value)
            payload = {
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "status": status,
                "employee_name": employee_name,
                "summary": {"total_tasks": len(tasks), "completed_tasks": completed}
            }
            httpx.post(
                f"{settings.liaison_agent_url}/workflow-complete",
                json=payload,
                timeout=10.0
            )
            logger.info(f"Notified Liaison of workflow {workflow_id} {status}")
        except Exception as notify_err:
            logger.warning(f"Could not notify Liaison of workflow {workflow_id} completion: {notify_err}")

    def _check_workflow_completion(self, workflow_id: str):
        """Check if all workflow tasks are complete."""
        try:
            with get_db() as db:
                workflow_doc = db.workflows.find_one({"workflow_id": workflow_id})
                if not workflow_doc:
                    return

                current_status = workflow_doc.get("status")
                
                tasks = list(db.tasks.find({"workflow_id": workflow_id}))
                
                if not tasks:
                    return
                
                all_completed = all(task["status"] == TaskStatus.COMPLETED.value for task in tasks)
                any_failed = any(task["status"] == TaskStatus.FAILED.value for task in tasks)
                
                if all_completed:
                    if current_status == WorkflowStatus.COMPLETED.value:
                        return
                    db.workflows.update_one(
                        {"workflow_id": workflow_id},
                        {"$set": {
                            "status": WorkflowStatus.COMPLETED.value,
                            "completed_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    logger.info(f"Workflow {workflow_id} completed successfully")
                    self._notify_liaison(
                        workflow_id,
                        workflow_doc["tenant_id"],
                        workflow_doc.get("employee_name", ""),
                        "COMPLETED",
                        tasks
                    )
                elif any_failed:
                    if current_status == WorkflowStatus.FAILED.value:
                        return
                    db.workflows.update_one(
                        {"workflow_id": workflow_id},
                        {"$set": {
                            "status": WorkflowStatus.FAILED.value,
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    logger.warning(f"Workflow {workflow_id} has failed tasks")
                    self._notify_liaison(
                        workflow_id,
                        workflow_doc["tenant_id"],
                        workflow_doc.get("employee_name", ""),
                        "FAILED",
                        tasks
                    )
                
        except Exception as e:
            logger.error(f"Error checking workflow completion: {e}")


# Global orchestrator instance
orchestrator_agent = OrchestratorAgent()
