# Provisioning Agent

**Deterministic Execution Agent for AgenticHR Multi-Agent Onboarding System**

## Overview

The Provisioning Agent is a specialized agent responsible for executing provisioning-related tasks in the AgenticHR multi-agent onboarding orchestration system. Unlike other agents that use AI for decision-making, the Provisioning Agent is **deterministic** and follows strict execution rules.

## Key Characteristics

### ✅ What This Agent DOES

- Executes provisioning tasks assigned by the Orchestrator Agent
- Creates HRIS employee records via n8n webhooks
- Creates IT access tickets via n8n webhooks
- Assigns system access roles via n8n webhooks
- Generates employee IDs via n8n webhooks
- Creates email accounts via n8n webhooks
- Requests laptop allocation via n8n webhooks
- Validates task payloads before execution
- Ensures idempotency (no duplicate operations)
- Returns structured JSON results
- Handles retries for network failures

### ❌ What This Agent DOES NOT DO

- Make planning decisions (handled by Orchestrator)
- Classify intent (handled by Liaison)
- Answer policy questions (handled by Guide)
- Use AI/LLM for decision-making (deterministic execution only)
- Directly call third-party APIs (only calls n8n webhooks)
- Schedule meetings (handled by Scheduler)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Orchestrator Agent                      │
│            (Plans & Delegates Tasks)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ Redis Stream: agent_stream:provisioning_agent
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Provisioning Agent                          │
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │  1. Receive Task from Redis Stream         │         │
│  │  2. Validate Payload                       │         │
│  │  3. Check Idempotency Cache                │         │
│  │  4. Execute via n8n Webhook                │         │
│  │  5. Return Result to Orchestrator          │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ HTTP POST
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    n8n Workflows                         │
│                                                          │
│  • /webhook/create-hr-record    → HRIS Integration      │
│  • /webhook/create-it-ticket    → IT System             │
│  • /webhook/assign-access       → IAM System            │
│  • /webhook/generate-id         → ID Generator          │
│  • /webhook/create-email        → Email System          │
│  • /webhook/request-laptop      → Asset Management      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
              External Systems
```

## Tech Stack

- **FastAPI** - REST API for health checks and testing
- **Redis** - Message streaming (inter-agent communication)
- **httpx** - Async HTTP client for n8n webhooks
- **Pydantic** - Data validation and settings
- **Loguru** - Structured logging
- **NO AI/LLM** - Deterministic execution only

## Message Flow

### Input Message (from Orchestrator)

```json
{
  "message_id": "msg_abc123",
  "workflow_id": "WF_acme_001",
  "tenant_id": "acme_corp",
  "from_agent": "orchestrator_agent",
  "to_agent": "provisioning_agent",
  "message_type": "task_request",
  "task": {
    "task_id": "task_hr_001",
    "task_type": "create_hr_record",
    "payload": {
      "employee_name": "John Doe",
      "employee_email": "john.doe@acme.com",
      "role": "Software Engineer",
      "department": "Engineering",
      "start_date": "2026-03-01"
    },
    "priority": 5,
    "retry_count": 0
  }
}
```

### Output Message (to Orchestrator)

```json
{
  "message_id": "msg_def456",
  "workflow_id": "WF_acme_001",
  "tenant_id": "acme_corp",
  "from_agent": "provisioning_agent",
  "to_agent": "orchestrator_agent",
  "message_type": "task_result",
  "data": {
    "task_id": "task_hr_001",
    "status": "success",
    "result": {
      "external_id": "HRIS-12345",
      "reference_url": "https://hris.acme.com/employees/12345",
      "details": {
        "employee_id": "EMP-2026-001",
        "created_at": "2026-02-22T16:30:00Z",
        "hris_system": "BambooHR"
      }
    },
    "error": null,
    "retry_possible": false
  }
}
```

## Supported Task Types

| Task Type | Description | n8n Webhook Endpoint |
|-----------|-------------|---------------------|
| `create_hr_record` | Create employee record in HRIS | `/webhook/create-hr-record` |
| `create_it_ticket` | Create IT access ticket | `/webhook/create-it-ticket` |
| `assign_access` | Assign system access roles | `/webhook/assign-access` |
| `generate_id` | Generate employee ID | `/webhook/generate-id` |
| `create_email` | Create email account | `/webhook/create-email` |
| `request_laptop` | Request laptop allocation | `/webhook/request-laptop` |

## Installation

### Prerequisites

- Python 3.9 or higher
- Redis (running on localhost:6379 or Docker)
- n8n (running on localhost:5678)

### Quick Setup

```powershell
# 1. Run setup script
.\setup.ps1

# 2. Update .env file with your configuration
# Edit .env and set:
# - REDIS_HOST, REDIS_PORT
# - N8N_WEBHOOK_BASE_URL

# 3. Start the agent
.\start.ps1
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your configuration
# Start the agent
python -m src.main
```

## Configuration

Edit `.env` file:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# n8n Webhook Configuration
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
N8N_API_KEY=

# API Configuration
API_HOST=0.0.0.0
API_PORT=8003

# Idempotency
ENABLE_IDEMPOTENCY_CHECK=true

# Retry Configuration
MAX_RETRIES=1
RETRY_DELAY_SECONDS=2
```

## API Endpoints

The agent exposes REST API endpoints for monitoring and testing:

### Health Check
```http
GET /api/v1/health
```

### Status
```http
GET /api/v1/status
```

### Execute Task (Testing)
```http
POST /api/v1/execute-task
Content-Type: application/json

{
  "workflow_id": "WF_test_001",
  "tenant_id": "acme_corp",
  "task": {
    "task_id": "task_001",
    "task_type": "create_hr_record",
    "payload": { ... }
  }
}
```

### API Documentation
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## Testing

```powershell
# Run test script
.\test_provisioning.bat

# Or manually
python test_provisioning.py
```

## Error Handling

### Validation Errors
- Missing required fields → `status: "failed"`, `retryable: false`
- Invalid task type → `status: "failed"`, `retryable: false`

### Network Errors
- Webhook timeout → `status: "failed"`, `retryable: true`
- Connection error → `status: "failed"`, `retryable: true`

### Idempotency
- Duplicate task detected → Returns cached result with `duplicate_detected: true`

## Logging

Logs are written to:
- Console (stdout)
- File: `logs/provisioning.log` (rotated at 10 MB, retained for 7 days)

## Security

- Never mixes tenant data (tenant_id always passed to webhooks)
- Never exposes API keys in logs
- Never logs sensitive employee data
- Validates all inputs before execution

## Multi-Tenancy

The agent is tenant-aware:
- Every task includes `tenant_id`
- All webhook calls include `tenant_id` in payload
- Idempotency cache is scoped per tenant
- No cross-tenant data leakage

## Development

### Project Structure

```
provisioning-agent/
├── src/
│   ├── agent/
│   │   └── provisioning.py      # Core agent logic
│   ├── api/
│   │   └── routes.py            # REST API routes
│   ├── config/
│   │   └── settings.py          # Configuration
│   ├── messaging/
│   │   └── redis_client.py      # Redis Stream client
│   ├── schemas/
│   │   └── mcp_message.py       # MCP message schemas
│   ├── webhooks/
│   │   └── n8n_client.py        # n8n webhook client
│   └── main.py                  # Entry point
├── logs/                        # Log files
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── setup.ps1                    # Setup script
├── start.ps1                    # Start script
└── test_provisioning.py         # Test script
```

## Monitoring

Check agent health:
```bash
curl http://localhost:8003/api/v1/health
```

Check agent status:
```bash
curl http://localhost:8003/api/v1/status
```

## Troubleshooting

### Agent not receiving messages
- Check Redis connection: `docker exec -it agentichr-redis redis-cli ping`
- Check Redis stream exists: `XINFO STREAM agent_stream:provisioning_agent`
- Check consumer group exists: `XINFO GROUPS agent_stream:provisioning_agent`

### Webhook calls failing
- Verify n8n is running: `curl http://localhost:5678/healthz`
- Check webhook endpoints are configured in n8n
- Check n8n logs for errors

### Task validation errors
- Check task payload has all required fields
- Check task_type is supported
- See logs for detailed validation errors

## Integration with Other Agents

- **Orchestrator** → Plans workflows, delegates tasks to Provisioning Agent
- **Liaison** → Routes user queries, never directly calls Provisioning Agent
- **Guide** → Answers policy questions, never calls Provisioning Agent
- **Scheduler** → Handles meeting scheduling, complementary to Provisioning

## License

MIT

## Support

For issues or questions, see the main AgenticHR documentation.
