"""
Scheduler Agent – Integration test script.

Sends sample task payloads directly to the agent's REST API
(bypasses Redis – useful when running the agent locally for the first time).

Usage:
    python test_scheduler.py
"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8004/api/v1"


async def check_health():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/health")
        print("\n[Health]")
        print(json.dumps(r.json(), indent=2))


async def check_status():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/status")
        print("\n[Status]")
        print(json.dumps(r.json(), indent=2))


async def test_schedule_meeting():
    payload = {
        "workflow_id": "wf_test_001",
        "tenant_id": "acme_corp",
        "task": {
            "task_id": "task_sched_001",
            "task_type": "schedule_meeting",
            "payload": {
                "meeting_title": "Induction Session – Alice Johnson",
                "description": "New employee induction meeting",
                "start_datetime": "2026-03-10T10:00:00",
                "end_datetime": "2026-03-10T11:00:00",
                "timezone": "America/New_York",
                "organizer_email": "hr@acme.com",
                "participants": [
                    "alice.johnson@acme.com",
                    "manager@acme.com",
                    "hr@acme.com"
                ],
                "meeting_type": "induction"
            }
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/execute-task", json=payload)
        print("\n[schedule_meeting]")
        print(json.dumps(r.json(), indent=2))


async def test_reschedule_meeting():
    payload = {
        "workflow_id": "wf_test_002",
        "tenant_id": "acme_corp",
        "task": {
            "task_id": "task_resched_001",
            "task_type": "reschedule_meeting",
            "payload": {
                "event_id": "google_cal_event_xyz",
                "meeting_title": "Induction Session – Alice Johnson (rescheduled)",
                "description": "Rescheduled induction meeting",
                "start_datetime": "2026-03-12T14:00:00",
                "end_datetime": "2026-03-12T15:00:00",
                "timezone": "America/New_York",
                "organizer_email": "hr@acme.com",
                "participants": [
                    "alice.johnson@acme.com",
                    "manager@acme.com"
                ],
                "meeting_type": "induction"
            }
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/execute-task", json=payload)
        print("\n[reschedule_meeting]")
        print(json.dumps(r.json(), indent=2))


async def test_cancel_meeting():
    payload = {
        "workflow_id": "wf_test_003",
        "tenant_id": "acme_corp",
        "task": {
            "task_id": "task_cancel_001",
            "task_type": "cancel_meeting",
            "payload": {
                "event_id": "google_cal_event_xyz",
                "organizer_email": "hr@acme.com",
                "timezone": "America/New_York",
                "participants": [
                    "alice.johnson@acme.com",
                    "manager@acme.com"
                ],
                "meeting_title": "Induction Session – Alice Johnson"
            }
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/execute-task", json=payload)
        print("\n[cancel_meeting]")
        print(json.dumps(r.json(), indent=2))


async def test_validation_failure():
    """Missing organizer_email – should return failed / retryable=false."""
    payload = {
        "workflow_id": "wf_test_004",
        "tenant_id": "acme_corp",
        "task": {
            "task_id": "task_invalid_001",
            "task_type": "schedule_meeting",
            "payload": {
                "meeting_title": "Missing fields meeting",
                "start_datetime": "2026-03-10T10:00:00",
                "end_datetime": "2026-03-10T09:00:00",   # end before start!
                "timezone": "UTC",
                "organizer_email": "",                    # missing!
                "participants": []                        # empty!
            }
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/execute-task", json=payload)
        print("\n[validation_failure]")
        print(json.dumps(r.json(), indent=2))


async def main():
    print("=" * 60)
    print("  Scheduler Agent – Integration Tests")
    print("=" * 60)

    await check_health()
    await check_status()
    await test_schedule_meeting()
    await test_reschedule_meeting()
    await test_cancel_meeting()
    await test_validation_failure()

    print("\n" + "=" * 60)
    print("  Tests complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
