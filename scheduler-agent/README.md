# Scheduler Agent

Deterministic scheduling execution agent for the **AgenticHR** multi-agent onboarding system.

---

## Overview

The Scheduler Agent is responsible for executing **all scheduling-related tasks** assigned by the Orchestrator Agent. It operates as a **deterministic execution engine** — no AI reasoning, no workflow decisions. It simply validates incoming task payloads, calls the correct n8n webhook, and returns structured results.

### What it does

| Task Type | n8n Endpoint | Action |
|---|---|---|
| `schedule_meeting` | `POST /schedule-meeting` | Create Google Calendar event + Meet link + send invites |
| `reschedule_meeting` | `POST /reschedule-meeting` | Update existing event, re-send invites |
| `cancel_meeting` | `POST /cancel-meeting` | Delete event, notify attendees |

### What it does NOT do

- Make workflow decisions
- Classify intent
- Answer policy questions
- Call Google Calendar / Meet APIs directly

---

## Architecture

```
Orchestrator Agent
       │
       │  Redis Stream: agent_stream:scheduler_agent
       ▼
  Scheduler Agent
       │
       │  HTTP POST (httpx)
       ▼
     n8n Webhooks
       │
       │  Google Calendar node
       ▼
  Google Calendar / Google Meet
       │
       │  event_id, hangoutLink, htmlLink, start, end
       ▼
  Scheduler Agent
       │
       │  Redis Stream: agent_stream:orchestrator_agent
       ▼
  Orchestrator Agent
```

---

## Quick Start

### 1. Setup

```powershell
cd scheduler-agent
.\setup.ps1
```

This will create a Python virtual environment, install dependencies, and copy `.env.example` to `.env`.

### 2. Configure

Edit `scheduler-agent\.env`:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
API_PORT=8004
```

### 3. Start

```powershell
.\start.ps1
```

The agent starts on **port 8004** and immediately begins listening to `agent_stream:scheduler_agent` in Redis.

### 4. Test

```powershell
python test_scheduler.py
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Agent identity |
| `GET` | `/api/v1/health` | Health / Redis status |
| `GET` | `/api/v1/status` | Runtime stats |
| `POST` | `/api/v1/execute-task` | Execute task directly (testing) |
| `GET` | `/api/v1/cache` | View idempotency cache |
| `DELETE` | `/api/v1/cache` | Clear idempotency cache |

---

## Input Message Format (from Orchestrator via Redis)

```json
{
  "action": "delegate_task",
  "workflow_id": "wf_onboard_001",
  "tenant_id": "acme_corp",
  "target_agent": "scheduler_agent",
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
      "participants": ["alice.johnson@acme.com", "manager@acme.com"],
      "meeting_type": "induction"
    }
  }
}
```

### Required fields by task type

| Field | `schedule_meeting` | `reschedule_meeting` | `cancel_meeting` |
|---|---|---|---|
| `meeting_title` | ✅ | ✅ | — |
| `start_datetime` | ✅ | ✅ | — |
| `end_datetime` | ✅ | ✅ | — |
| `timezone` | ✅ | ✅ | ✅ |
| `organizer_email` | ✅ | ✅ | ✅ |
| `participants` | ✅ (≥1) | ✅ (≥1) | — |
| `event_id` | — | ✅ | ✅ |

---

## Output Format (strict)

```json
{
  "action": "task_result",
  "workflow_id": "wf_onboard_001",
  "tenant_id": "acme_corp",
  "task_id": "task_sched_001",
  "status": "success",
  "result": {
    "event_id": "abc123xyz",
    "meet_link": "https://meet.google.com/xxx-yyyy-zzz",
    "start_datetime": "2026-03-10T10:00:00",
    "end_datetime": "2026-03-10T11:00:00",
    "calendar_url": "https://www.google.com/calendar/event?eid=...",
    "details": {
      "meeting_title": "Induction Session – Alice Johnson",
      "participants": ["alice.johnson@acme.com", "manager@acme.com"]
    }
  },
  "error": null,
  "retryable": false
}
```

---

## n8n Workflow Setup

### `/schedule-meeting`

1. **Webhook trigger** → path: `schedule-meeting`
2. **Google Calendar node** → operation: `Create Event`
   - Enable **"Add Google Meet link"** (sets `conferenceDataVersion=1`)
   - Map: `summary`, `description`, `start.dateTime`, `end.dateTime`, `attendees`
   - Set `timeZone` from payload
3. **Respond to Webhook** → return:
   ```json
   {
     "id": "{{ $node['Google Calendar'].json.id }}",
     "hangoutLink": "{{ $node['Google Calendar'].json.hangoutLink }}",
     "start": { "dateTime": "{{ $node['Google Calendar'].json.start.dateTime }}" },
     "end": { "dateTime": "{{ $node['Google Calendar'].json.end.dateTime }}" },
     "htmlLink": "{{ $node['Google Calendar'].json.htmlLink }}"
   }
   ```

### `/reschedule-meeting`

1. **Webhook trigger** → path: `reschedule-meeting`
2. **Google Calendar node** → operation: `Update Event`
   - Use `event_id` from payload as the Event ID
3. **Respond to Webhook** → same shape as above

### `/cancel-meeting`

1. **Webhook trigger** → path: `cancel-meeting`
2. **Google Calendar node** → operation: `Delete Event`
   - Use `event_id` from payload
3. **Respond to Webhook** → `{ "status": "cancelled" }`

> All Google account credentials must be stored in **n8n Credential Manager** and never sent in webhook payloads.

---

## Validation Rules

- `start_datetime` and `end_datetime` must be valid ISO 8601.
- `end_datetime` must be strictly after `start_datetime`.
- `participants` must contain at least one email for schedule / reschedule.
- `organizer_email` and `timezone` are always required.
- `event_id` is required for reschedule and cancel.

Validation failures return `status: "failed"`, `retryable: false`.

---

## Error Handling

| Error Type | `retryable` |
|---|---|
| Validation failure | `false` |
| n8n 4xx response | `false` |
| Network / timeout error | `true` |
| n8n 5xx response | `true` (after 1 auto-retry) |

---

## Security

- `tenant_id` is always included in every webhook call.
- No API credentials are ever logged or returned in responses.
- Tenant data is never mixed.
- Internal system architecture is not exposed in API responses.

---

## Project Structure

```
scheduler-agent/
├── src/
│   ├── agent/
│   │   └── scheduler.py          # Core agent – validation, dispatch, handlers
│   ├── api/
│   │   └── routes.py             # FastAPI REST endpoints
│   ├── config/
│   │   └── settings.py           # Pydantic settings (reads .env)
│   ├── messaging/
│   │   └── redis_client.py       # Redis stream reader / publisher
│   ├── schemas/
│   │   └── mcp_message.py        # MCP message + task payload models
│   ├── webhooks/
│   │   └── n8n_client.py         # n8n webhook HTTP client
│   └── main.py                   # FastAPI app + lifespan + uvicorn entry
├── logs/                         # Runtime log files
├── .env.example                  # Environment variable template
├── requirements.txt
├── setup.ps1                     # One-time setup script
├── start.ps1                     # Start agent script
└── test_scheduler.py             # Integration test script
```
