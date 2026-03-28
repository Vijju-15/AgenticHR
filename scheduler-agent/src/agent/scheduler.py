"""Core Scheduler Agent – Deterministic execution agent for scheduling tasks.

Responsibilities
----------------
- Listen to Redis Streams for delegated scheduling tasks from Orchestrator.
- Validate every payload strictly before any external call.
- Call n8n webhook endpoints for Google Calendar / Meet operations.
- Return structured MCP task_result messages to Orchestrator.
- Never use AI / LLM – purely deterministic execution.
- Enforce tenant isolation by always including tenant_id in webhook calls.

Supported task_type values
--------------------------
  schedule_meeting      → POST /schedule-meeting  (full payload required)
  schedule_induction    → POST /schedule-meeting  (normalises orchestrator payload)
  schedule_manager_intro→ POST /schedule-meeting  (normalises orchestrator payload)
  schedule_hr_session   → POST /schedule-meeting  (normalises orchestrator payload)
  reschedule_meeting    → POST /reschedule-meeting
  cancel_meeting        → POST /cancel-meeting

Payload normalisation
---------------------
The Orchestrator sends a simplified payload for scheduling tasks:
  { employee_email, employee_name, manager_email, start_date, meeting_type }

The agent auto-builds the full meeting payload from these fields so that
n8n receives a complete, validated request every time.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from src.config.settings import settings
from src.schemas.mcp_message import (
    AgentType,
    MCPMessage,
    TaskPayload,
    TaskResult,
)
from src.webhooks.n8n_client import n8n_client
from src.messaging.redis_client import redis_client


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def _parse_iso8601(value: str) -> Optional[datetime]:
    """
    Parse an ISO 8601 datetime string.

    Accepts formats with or without trailing 'Z' / UTC offset.
    Returns None on failure.
    """
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Scheduler Agent
# ---------------------------------------------------------------------------

class SchedulerAgent:
    """
    Scheduler Agent – Deterministic execution agent.

    Execution flow for every incoming message:
      1. Parse MCP message from Redis stream.
      2. Validate task payload (all fields, date logic, participants).
      3. Check idempotency cache to avoid duplicate calendar events.
      4. Dispatch to correct handler (schedule / reschedule / cancel).
      5. Call n8n webhook.
      6. Package result as TaskResult and publish to Orchestrator stream.
    """

    # In-memory idempotency cache  {"{tenant_id}:{task_id}" -> result_dict}
    _processed_tasks: Dict[str, Dict[str, Any]] = {}

    # Task types that come from Orchestrator as semantic names
    # and map to the schedule_meeting handler after payload normalisation.
    SCHEDULE_ALIASES = {
        "schedule_induction":     "induction",
        "schedule_manager_intro": "manager_intro",
        "schedule_hr_session":    "hr_session",
    }

    # Default meeting durations (minutes) per meeting type
    DEFAULT_DURATION_MINUTES: Dict[str, int] = {
        "induction":     60,
        "manager_intro": 30,
        "hr_session":    45,
    }

    # Default meeting start hour (local, 24h) when only a date is provided
    DEFAULT_MEETING_HOUR = 10

    def __init__(self) -> None:
        self.agent_type = AgentType.SCHEDULER

        self.task_handlers = {
            # Generic / full-payload tasks
            "schedule_meeting":     self._handle_schedule_meeting,
            "reschedule_meeting":   self._handle_reschedule_meeting,
            "cancel_meeting":       self._handle_cancel_meeting,
            # Orchestrator semantic aliases – all normalised to schedule_meeting
            "schedule_induction":     self._handle_schedule_meeting,
            "schedule_manager_intro": self._handle_schedule_meeting,
            "schedule_hr_session":    self._handle_schedule_meeting,
        }

        logger.info("Scheduler Agent initialised (deterministic mode)")
        logger.info(
            f"Supported task types: {list(self.task_handlers.keys())}"
        )

    # ------------------------------------------------------------------
    # Idempotency helpers
    # ------------------------------------------------------------------

    def check_idempotency(
        self, task_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return cached result if this task was already executed."""
        if not settings.enable_idempotency_check:
            return None
        return self._processed_tasks.get(f"{tenant_id}:{task_id}")

    def cache_result(
        self, task_id: str, tenant_id: str, result: Dict[str, Any]
    ) -> None:
        """Store result in idempotency cache."""
        if settings.enable_idempotency_check:
            self._processed_tasks[f"{tenant_id}:{task_id}"] = result
            logger.debug(f"Cached result for task {task_id}")

    # ------------------------------------------------------------------
    # Payload normalisation
    # ------------------------------------------------------------------

    def _normalize_payload(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise an Orchestrator-style simplified payload into the full
        meeting payload shape expected by n8n webhooks.

        Orchestrator sends:
            { employee_email, employee_name, manager_email,
              start_date, meeting_type }

        This method builds:
            { meeting_title, description, start_datetime, end_datetime,
              timezone, organizer_email, participants, meeting_type }

        If the payload already contains start_datetime / end_datetime
        (i.e. came from a direct API call), it is returned unchanged.
        """
        # Already a full payload – nothing to do
        if payload.get("start_datetime") and payload.get("end_datetime"):
            return payload

        import copy
        from datetime import timedelta

        p = copy.deepcopy(payload)

        # --- Determine meeting_type ---
        if task_type in self.SCHEDULE_ALIASES:
            p.setdefault("meeting_type", self.SCHEDULE_ALIASES[task_type])
        meeting_type = p.get("meeting_type", "induction")

        # --- Build meeting_title ---
        title_map = {
            "induction":     "Induction Meeting",
            "manager_intro": "Manager Introduction Meeting",
            "hr_session":    "HR Onboarding Session",
        }
        employee_name = p.get("employee_name", "New Employee")
        p.setdefault(
            "meeting_title",
            f"{title_map.get(meeting_type, 'Onboarding Meeting')} – {employee_name}"
        )

        # --- Build description ---
        p.setdefault(
            "description",
            f"AgenticHR onboarding: {p['meeting_title']}"
        )

        # --- Build start_datetime + end_datetime from start_date ---
        start_date_str = p.get("start_date", "")
        try:
            start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            # Fallback: use tomorrow
            start_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        start_dt = start_date.replace(hour=self.DEFAULT_MEETING_HOUR, minute=0, second=0)
        duration_mins = self.DEFAULT_DURATION_MINUTES.get(meeting_type, 60)
        end_dt = start_dt + timedelta(minutes=duration_mins)

        p["start_datetime"] = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        p["end_datetime"]   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # --- Build participants list ---
        if not p.get("participants"):
            participants = []
            if p.get("employee_email"):
                participants.append(p["employee_email"])
            if p.get("manager_email"):
                participants.append(p["manager_email"])
            p["participants"] = participants

        # --- organizer_email falls back to manager_email ---
        if not p.get("organizer_email"):
            p["organizer_email"] = p.get("manager_email", "")

        # --- Default timezone ---
        p.setdefault("timezone", "UTC")

        return p

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_task_payload(
        self, task: TaskPayload
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate task payload before calling any webhook.

        NOTE: Call _normalize_payload() on task.payload BEFORE this method
        so the full field set is present.

        Returns:
            (is_valid: bool, error_message: str | None)
        """
        if not task.task_id:
            return False, "Missing required field: task_id"

        if not task.task_type:
            return False, "Missing required field: task_type"

        if task.task_type not in self.task_handlers:
            return False, f"Unknown task_type: '{task.task_type}'"

        p = task.payload

        # --- Fields required for ALL task types ---
        if not p.get("organizer_email"):
            return False, "Missing required field: organizer_email"

        if not p.get("timezone"):
            return False, "Missing required field: timezone"

        # Task types that need full scheduling fields (after normalisation)
        schedule_task_types = {
            "schedule_meeting",
            "reschedule_meeting",
            "schedule_induction",
            "schedule_manager_intro",
            "schedule_hr_session",
        }

        if task.task_type in schedule_task_types:
            for field in ("meeting_title", "start_datetime", "end_datetime"):
                if not p.get(field):
                    return False, f"Missing required field: {field}"

            start = _parse_iso8601(p["start_datetime"])
            end = _parse_iso8601(p["end_datetime"])

            if start is None:
                return False, (
                    f"Invalid start_datetime format: {p['start_datetime']} "
                    "(expected ISO 8601)"
                )

            if end is None:
                return False, (
                    f"Invalid end_datetime format: {p['end_datetime']} "
                    "(expected ISO 8601)"
                )

            start_naive = start.replace(tzinfo=None)
            end_naive = end.replace(tzinfo=None)
            if end_naive <= start_naive:
                return False, (
                    f"end_datetime ({p['end_datetime']}) must be after "
                    f"start_datetime ({p['start_datetime']})"
                )

            participants = p.get("participants", [])
            if not isinstance(participants, list) or len(participants) == 0:
                return False, "At least one participant is required"

        # --- Fields required for reschedule / cancel ---
        if task.task_type in ("reschedule_meeting", "cancel_meeting"):
            if not p.get("event_id"):
                return False, (
                    f"Missing required field for {task.task_type}: event_id"
                )

        return True, None

    # ------------------------------------------------------------------
    # Main processing entry point
    # ------------------------------------------------------------------

    async def process_task(self, message: MCPMessage) -> TaskResult:
        """
        Process an incoming delegated task from Orchestrator.

        Args:
            message: Parsed MCP message

        Returns:
            Completed TaskResult to be published back to Orchestrator
        """
        task = message.task
        workflow_id = message.workflow_id
        tenant_id = message.tenant_id

        if not task:
            logger.error("Received message without task payload")
            return self._error_result(
                task_id="unknown",
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                error="No task payload in message",
                retryable=False,
            )

        task_id = task.task_id
        logger.info(f"Processing task {task_id}  type={task.task_type}")

        # --- Idempotency check ---
        cached = self.check_idempotency(task_id, tenant_id)
        if cached:
            logger.info(f"Task {task_id} already processed – returning cached result")
            cached_copy = dict(cached)
            details = cached_copy.get("details", {})
            if isinstance(details, dict):
                details["duplicate_detected"] = True
            return TaskResult(
                task_id=task_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                from_agent=self.agent_type,
                status="success",
                result=cached_copy,
                retry_possible=False,
            )

        # --- Normalise payload (converts Orchestrator short-form to full meeting shape) ---
        task.payload = self._normalize_payload(task.task_type, task.payload)
        logger.debug(f"Normalised payload for task {task_id}: {task.payload}")

        # --- Payload validation ---
        is_valid, error_msg = self.validate_task_payload(task)
        if not is_valid:
            logger.error(f"Validation failed for task {task_id}: {error_msg}")
            return self._error_result(
                task_id=task_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                error=error_msg,
                retryable=False,
            )

        # --- Execute ---
        try:
            handler = self.task_handlers[task.task_type]
            result = await handler(tenant_id, task.payload)

            self.cache_result(task_id, tenant_id, result)

            return TaskResult(
                task_id=task_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                from_agent=self.agent_type,
                status="success",
                result=result,
                retry_possible=False,
            )

        except Exception as exc:
            logger.error(f"Task {task_id} execution failed: {exc}")

            # Network / timeout errors are retryable; all others are not
            is_net = any(
                kw in str(exc).lower()
                for kw in ("network", "timeout", "connection", "connect")
            )
            return self._error_result(
                task_id=task_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                error=str(exc),
                retryable=is_net,
            )

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_schedule_meeting(
        self, tenant_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle schedule_meeting task.

        Calls n8n /schedule-meeting which:
          - Creates Google Calendar event
          - Generates Google Meet link automatically
          - Sends calendar invites to all participants
        """
        logger.info(
            f"Scheduling meeting '{payload.get('meeting_title')}' "
            f"for tenant {tenant_id}"
        )

        response = await n8n_client.schedule_meeting(tenant_id, payload)

        return {
            "event_id": response.get("event_id", ""),
            "meet_link": response.get("meet_link", ""),
            "start_datetime": response.get("start_datetime", payload.get("start_datetime", "")),
            "end_datetime": response.get("end_datetime", payload.get("end_datetime", "")),
            "calendar_url": response.get("calendar_url", ""),
            "details": {
                "meeting_title": payload.get("meeting_title", ""),
                "meeting_type": payload.get("meeting_type", ""),
                "participants": payload.get("participants", []),
                "organizer_email": payload.get("organizer_email", ""),
                "timezone": payload.get("timezone", ""),
            },
        }

    async def _handle_reschedule_meeting(
        self, tenant_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle reschedule_meeting task.

        Calls n8n /reschedule-meeting which updates the existing
        Google Calendar event and re-sends invites if needed.
        Requires payload.event_id.
        """
        logger.info(
            f"Rescheduling event {payload.get('event_id')} "
            f"for tenant {tenant_id}"
        )

        response = await n8n_client.reschedule_meeting(tenant_id, payload)

        return {
            "event_id": response.get("event_id", payload.get("event_id", "")),
            "meet_link": response.get("meet_link", ""),
            "start_datetime": response.get(
                "start_datetime", payload.get("start_datetime", "")
            ),
            "end_datetime": response.get(
                "end_datetime", payload.get("end_datetime", "")
            ),
            "calendar_url": response.get("calendar_url", ""),
            "details": {
                "meeting_title": payload.get("meeting_title", ""),
                "meeting_type": payload.get("meeting_type", ""),
                "participants": payload.get("participants", []),
                "organizer_email": payload.get("organizer_email", ""),
                "timezone": payload.get("timezone", ""),
                "rescheduled": True,
            },
        }

    async def _handle_cancel_meeting(
        self, tenant_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cancel_meeting task.

        Calls n8n /cancel-meeting which deletes the Google Calendar
        event and notifies attendees.
        Requires payload.event_id.
        """
        logger.info(
            f"Cancelling event {payload.get('event_id')} "
            f"for tenant {tenant_id}"
        )

        response = await n8n_client.cancel_meeting(tenant_id, payload)

        return {
            "event_id": payload.get("event_id", ""),
            "meet_link": "",
            "start_datetime": "",
            "end_datetime": "",
            "calendar_url": "",
            "details": {
                "cancelled": True,
                "cancellation_status": response.get("status", "cancelled"),
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "meeting_title": payload.get("meeting_title", ""),
                "participants": payload.get("participants", []),
            },
        }

    # ------------------------------------------------------------------
    # Error factory
    # ------------------------------------------------------------------

    def _error_result(
        self,
        task_id: str,
        workflow_id: str,
        tenant_id: str,
        error: str,
        retryable: bool,
    ) -> TaskResult:
        """Build a failed TaskResult."""
        return TaskResult(
            task_id=task_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            from_agent=self.agent_type,
            status="failure",
            result={},
            error=error,
            retry_possible=retryable,
        )

    # ------------------------------------------------------------------
    # Main listener loop
    # ------------------------------------------------------------------

    async def start_listening(self) -> None:
        """
        Blocking async loop – reads Redis stream and dispatches tasks.

        Started as a background task during app lifespan.
        """
        logger.info("Scheduler Agent listener starting …")
        logger.info(
            f"Subscribed to stream: agent_stream:{self.agent_type.value}"
        )

        while True:
            try:
                messages = redis_client.read_messages(count=1, block=1000)

                if not messages:
                    await asyncio.sleep(0.1)
                    continue

                for msg in messages:
                    try:
                        message = MCPMessage(**msg["data"])
                        logger.info(
                            f"Received {message.message_type.value} "
                            f"from {message.from_agent.value} "
                            f"[msg_id={message.message_id}]"
                        )

                        result = await self.process_task(message)
                        redis_client.publish_task_result(result)

                        logger.info(
                            f"Task {result.task_id} completed "
                            f"– status={result.status}"
                        )

                    except Exception as exc:
                        logger.error(f"Error processing message {msg.get('id')}: {exc}")

                await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                logger.info("Scheduler Agent listener cancelled – shutting down")
                break
            except Exception as exc:
                logger.error(f"Unexpected error in listener loop: {exc}")
                await asyncio.sleep(1)


# Singleton instance
scheduler_agent = SchedulerAgent()
