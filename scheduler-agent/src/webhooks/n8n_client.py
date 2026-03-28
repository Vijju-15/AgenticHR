"""n8n Webhook client for Scheduler Agent external integrations.

Webhooks consumed:
  POST /schedule-meeting    – Create Google Calendar event + Meet link
  POST /reschedule-meeting  – Update existing event
  POST /cancel-meeting      – Delete / cancel existing event
"""

import httpx
import time
from typing import Dict, Any, Optional
from loguru import logger

from src.config.settings import settings


class N8nWebhookClient:
    """Client for calling n8n scheduler webhooks."""

    # ---------------------------------------------------------------
    # Webhook endpoint paths (n8n workflow trigger paths)
    # ---------------------------------------------------------------
    ENDPOINT_SCHEDULE = "/schedule-meeting"
    ENDPOINT_RESCHEDULE = "/reschedule-meeting"
    ENDPOINT_CANCEL = "/cancel-meeting"

    def __init__(self):
        """Initialise n8n webhook client."""
        self.base_url = settings.n8n_webhook_base_url
        self.timeout = settings.webhook_timeout_seconds
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay_seconds

        self.headers: Dict[str, str] = {}
        if settings.n8n_api_key:
            self.headers["Authorization"] = f"Bearer {settings.n8n_api_key}"

        logger.info(f"n8n webhook client initialised – base URL: {self.base_url}")

    # ---------------------------------------------------------------
    # Low-level HTTP caller
    # ---------------------------------------------------------------

    async def call_webhook(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retry: bool = True,
    ) -> Dict[str, Any]:
        """
        POST to an n8n webhook endpoint.

        Args:
            endpoint: Path appended to base URL (e.g. '/schedule-meeting')
            payload:  Request body
            retry:    Whether to retry once on transient failure

        Returns:
            Parsed JSON response dict

        Raises:
            Exception: Propagated after retries are exhausted
        """
        url = f"{self.base_url}{endpoint}"
        max_attempts = (self.max_retries + 1) if retry else 1
        attempt = 0

        while attempt < max_attempts:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        f"→ n8n {endpoint}  attempt {attempt + 1}/{max_attempts}"
                    )
                    response = await client.post(url, json=payload, headers=self.headers)
                    response.raise_for_status()

                    # Guard against empty body (e.g. workflow crashed before Respond node)
                    raw = response.text.strip()
                    if not raw:
                        logger.warning(f"Empty response body from {endpoint} – returning empty dict")
                        return {}
                    result = response.json()
                    logger.info(f"n8n webhook success: {endpoint}")
                    logger.info(f"n8n raw response from {endpoint}: {result}")
                    return result

            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                logger.error(
                    f"HTTP {code} from {endpoint}: {exc.response.text}"
                )
                # 4xx – do not retry; surface immediately
                if 400 <= code < 500:
                    raise Exception(
                        f"Webhook validation error [{code}]: {exc.response.text}"
                    )
                attempt += 1
                if attempt < max_attempts:
                    logger.info(f"Retrying in {self.retry_delay}s …")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(
                        f"Webhook {endpoint} failed after {max_attempts} attempts: {exc}"
                    )

            except httpx.RequestError as exc:
                logger.error(f"Network error calling {endpoint}: {exc}")
                attempt += 1
                if attempt < max_attempts:
                    logger.info(f"Retrying in {self.retry_delay}s …")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(
                        f"Network error on {endpoint} after {max_attempts} attempts: {exc}"
                    )

            except Exception as exc:
                logger.error(f"Unexpected error calling {endpoint}: {exc}")
                raise

    # ---------------------------------------------------------------
    # High-level scheduling methods
    # ---------------------------------------------------------------

    async def schedule_meeting(
        self,
        tenant_id: str,
        meeting_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a Google Calendar event via n8n.

        n8n workflow MUST:
          1. Use Google Calendar node with "Create Event" operation.
          2. Enable "Add Google Meet link" (conferenceDataVersion=1).
          3. Send calendar invites to all attendees.
          4. Return: event_id, hangoutLink, start, end, htmlLink.

        Args:
            tenant_id:       Tenant identifier passed to n8n.
            meeting_payload: Full meeting detail dict from task payload.

        Returns:
            Dict with keys: event_id, meet_link, start_datetime,
                            end_datetime, calendar_url
        """
        body = {
            "task_type": "schedule_meeting",
            "tenant_id": tenant_id,
            "payload": meeting_payload,
        }
        response = await self.call_webhook(self.ENDPOINT_SCHEDULE, body)
        return self._normalise_schedule_response(response)

    async def reschedule_meeting(
        self,
        tenant_id: str,
        meeting_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing Google Calendar event via n8n.

        Requires meeting_payload to include event_id.

        n8n workflow MUST:
          1. Use Google Calendar "Update Event" node.
          2. Re-send invites if attendees changed.
          3. Return updated event metadata.

        Returns:
            Dict with updated meeting metadata.
        """
        body = {
            "task_type": "reschedule_meeting",
            "tenant_id": tenant_id,
            "payload": meeting_payload,
        }
        response = await self.call_webhook(self.ENDPOINT_RESCHEDULE, body)
        return self._normalise_schedule_response(response)

    async def cancel_meeting(
        self,
        tenant_id: str,
        meeting_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Cancel / delete a Google Calendar event via n8n.

        Requires meeting_payload to include event_id.

        n8n workflow MUST:
          1. Use Google Calendar "Delete Event" node.
          2. Notify attendees of cancellation.
          3. Return cancellation confirmation.

        Returns:
            Dict with cancellation confirmation.
        """
        body = {
            "task_type": "cancel_meeting",
            "tenant_id": tenant_id,
            "payload": meeting_payload,
        }
        return await self.call_webhook(self.ENDPOINT_CANCEL, body)

    # ---------------------------------------------------------------
    # Response normalisation
    # ---------------------------------------------------------------

    @staticmethod
    def _normalise_schedule_response(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map n8n Google Calendar node output to a canonical shape.

        n8n Google Calendar node typically returns:
            id, hangoutLink, start.dateTime, end.dateTime, htmlLink

        We normalise these to consistent field names used in task results.
        """
        # Unwrap n8n {status, data} envelope when present
        raw = raw.get("data", raw) if isinstance(raw.get("data"), dict) else raw

        # Handle both flat and nested n8n response shapes
        start_raw = raw.get("start") or {}
        end_raw = raw.get("end") or {}

        return {
            "event_id": raw.get("id") or raw.get("event_id", ""),
            "meet_link": raw.get("hangoutLink") or raw.get("meet_link", ""),
            "start_datetime": (
                start_raw.get("dateTime")
                if isinstance(start_raw, dict)
                else raw.get("start_datetime", "")
            ),
            "end_datetime": (
                end_raw.get("dateTime")
                if isinstance(end_raw, dict)
                else raw.get("end_datetime", "")
            ),
            "calendar_url": raw.get("htmlLink") or raw.get("calendar_url", ""),
        }


# Singleton instance
n8n_client = N8nWebhookClient()
