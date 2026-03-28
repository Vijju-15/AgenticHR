# Provisioning Agent - Implementation Summary

## Overview

The **Provisioning Agent** is a deterministic execution agent in the AgenticHR multi-agent onboarding system. It executes provisioning-related tasks by calling n8n webhooks for external integrations.

---

## Key Design Principles

### 1. Deterministic Execution (No AI/LLM)

Unlike Orchestrator and Liaison agents that use Gemini AI for decision-making, the Provisioning Agent is **purely deterministic**:

- No AI/LLM calls
- No natural language processing
- No intent classification
- No decision-making logic
- Follows strict execution rules based on task type

**Why?** Provisioning tasks are structured and predictable. Using AI would add unnecessary latency, cost, and potential for hallucinations.

### 2. Task-Based Architecture

The agent operates on a simple model:

```
Input: Structured Task → Validation → Execution → Output: Structured Result
```

No reasoning or planning involved.

### 3. n8n Integration Layer

All external integrations go through n8n webhooks:

- **Decouples** agent from third-party APIs
- **Enables** visual workflow management in n8n
- **Allows** non-developers to modify integrations
- **Provides** error handling and retry logic at n8n level

### 4. Idempotency

Every task is tracked to prevent duplicate operations:

- Task results are cached by `tenant_id:task_id`
- Duplicate requests return cached result immediately
- Prevents accidental duplicate provisioning (e.g., creating 2 HRIS records)

---

## Architecture Components

### 1. Core Agent (`src/agent/provisioning.py`)

**Responsibilities:**
- Listen to Redis stream for incoming tasks
- Validate task payloads
- Check idempotency cache
- Execute tasks via webhook client
- Return results to Orchestrator

**Key Methods:**
- `process_task()` - Main task processing logic
- `validate_task_payload()` - Ensure required fields present
- `check_idempotency()` - Check if task already executed
- `_handle_create_hr_record()` - Execute HR record creation
- `_handle_create_it_ticket()` - Execute IT ticket creation
- ... (one handler per task type)

### 2. Webhook Client (`src/webhooks/n8n_client.py`)

**Responsibilities:**
- Call n8n webhook endpoints via HTTP POST
- Handle retries for network errors
- Timeout management
- Error classification (4xx = non-retryable, 5xx = retryable)

**Key Methods:**
- `call_webhook()` - Generic webhook caller with retry logic
- `create_hr_record()` - Specific wrapper for HR record creation
- `create_it_ticket()` - Specific wrapper for IT ticket creation
- ... (one wrapper per task type)

### 3. Redis Client (`src/messaging/redis_client.py`)

**Responsibilities:**
- Read messages from Redis stream
- Publish results back to Orchestrator
- Manage consumer groups
- Acknowledge processed messages

**Key Methods:**
- `read_messages()` - Read from provisioning agent stream
- `publish_task_result()` - Send result to Orchestrator
- `health_check()` - Verify Redis connection

### 4. API Layer (`src/api/routes.py`)

**Responsibilities:**
- Health check endpoint
- Status monitoring endpoint
- Direct task execution (for testing)
- Cache inspection (for debugging)

**Endpoints:**
- `GET /api/v1/health` - Health check
- `GET /api/v1/status` - Agent status
- `POST /api/v1/execute-task` - Execute task directly (bypass Redis)
- `GET /api/v1/cache` - View cached tasks
- `DELETE /api/v1/cache` - Clear cache

---

## Message Flow

### 1. Orchestrator → Provisioning Agent

Via Redis stream: `agent_stream:provisioning_agent`

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
    "payload": { ... }
  }
}
```

### 2. Provisioning Agent → n8n Webhook

Via HTTP POST to n8n:

```json
POST http://localhost:5678/webhook/create-hr-record
{
  "tenant_id": "acme_corp",
  "employee_data": { ... }
}
```

### 3. n8n → External System (HRIS, IT, etc.)

n8n workflow handles integration with external systems.

### 4. Provisioning Agent → Orchestrator

Via Redis stream: `agent_stream:orchestrator_agent`

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
      "reference_url": "...",
      "details": { ... }
    }
  }
}
```

---

## Task Validation Rules

Each task type has specific required fields:

### `create_hr_record`
- `employee_name` (required)
- `employee_email` (required)
- `role` (required)
- `department` (required)

### `create_it_ticket`
- `employee_id` (required)
- `employee_name` (required)

### `assign_access`
- `employee_id` (required)
- `access_roles` (required)

### `generate_id`
- Any employee info (flexible)

### `create_email`
- `employee_name` (required)
- `employee_email` (required)

### `request_laptop`
- `employee_id` (required)

---

## Error Handling Strategy

### Validation Errors
- Missing required fields → `status: "failed"`, `retryable: false`
- Unknown task type → `status: "failed"`, `retryable: false`

### Network Errors
- HTTP timeout → `status: "failed"`, `retryable: true`
- Connection refused → `status: "failed"`, `retryable: true`
- Automatic retry (once) before returning failure

### 4xx HTTP Errors
- Bad request → `status: "failed"`, `retryable: false`
- No automatic retry (likely data issue)

### 5xx HTTP Errors
- Server error → `status: "failed"`, `retryable: true`
- Automatic retry (once)

---

## Idempotency Implementation

### Cache Structure
```python
_processed_tasks = {
    "acme_corp:task_hr_001": {
        "external_id": "HRIS-12345",
        "reference_url": "...",
        "details": { ... }
    }
}
```

### Cache Key Format
`{tenant_id}:{task_id}`

### Cache Behavior
1. Check cache before execution
2. If found → Return cached result + `duplicate_detected: true`
3. If not found → Execute task → Cache result → Return

### Cache Limitations
- In-memory only (lost on restart)
- Future enhancement: Redis-based cache for persistence

---

## Multi-Tenancy

Every operation is scoped by `tenant_id`:

1. **Message Validation** - Ensures `tenant_id` present
2. **Webhook Calls** - Always include `tenant_id` in payload
3. **Idempotency Cache** - Scoped per tenant
4. **Error Handling** - Tenant context in all logs

**Security:** No cross-tenant data leakage possible.

---

## Tech Stack Rationale

| Technology | Purpose | Why Not Alternatives? |
|------------|---------|---------------------|
| FastAPI | REST API | Modern, async, auto-docs |
| Redis | Message streaming | Already used by other agents |
| httpx | HTTP client | Async support, better than requests |
| Pydantic | Data validation | Type safety, auto-validation |
| Loguru | Logging | Better than stdlib logging |
| **NO AI** | N/A | Deterministic tasks don't need AI |

---

## Performance Considerations

- **Message Processing:** Non-blocking I/O using async/await
- **Webhook Calls:** Timeout after 30 seconds (configurable)
- **Retry Logic:** 1 automatic retry (configurable)
- **Concurrency:** Single worker (can scale horizontally)

---

## Security Measures

1. **API Key Protection:** n8n API key in environment variable
2. **Tenant Isolation:** All operations scoped by tenant_id
3. **No Credential Logging:** Sensitive data never logged
4. **Input Validation:** All payloads validated before execution
5. **Error Sanitization:** Stack traces not exposed to client

---

## Deployment Modes

### Development (Current)
- Single process
- In-memory cache
- File-based logging
- Auto-reload on code changes

### Production (Future)
- Multiple workers
- Redis-based cache
- Centralized logging (e.g., ELK)
- Load balancer in front

---

## Testing Strategy

### Unit Tests (Future)
- Mock n8n webhook calls
- Test validation logic
- Test idempotency logic

### Integration Tests (Current)
- `test_provisioning.py` - Tests against live agent
- Health check validation
- Status endpoint validation

### End-to-End Tests (Future)
- Orchestrator → Provisioning → n8n → Mock external system

---

## Monitoring & Observability

### Logs
- **Location:** `logs/provisioning.log`
- **Format:** Structured JSON-like
- **Rotation:** 10 MB, 7 days retention

### Metrics (Future)
- Task execution count per type
- Task success/failure rate
- Average execution time
- Idempotency cache hit rate

### Health Checks
- `/api/v1/health` - Redis connection status
- `/api/v1/status` - Agent configuration and stats

---

## Future Enhancements

1. **Persistent Idempotency Cache** - Use Redis instead of in-memory
2. **Webhook Circuit Breaker** - Stop calling failing webhooks
3. **Task Queue Prioritization** - High-priority tasks first
4. **Dead Letter Queue** - Failed tasks moved to DLQ
5. **Prometheus Metrics** - Export metrics for monitoring
6. **OpenTelemetry Tracing** - Distributed tracing across agents

---

## Integration Points

### With Orchestrator Agent
- **Input:** Tasks via Redis stream `agent_stream:provisioning_agent`
- **Output:** Results via Redis stream `agent_stream:orchestrator_agent`

### With n8n
- **Output:** HTTP POST to `/webhook/*` endpoints
- **Input:** JSON response with operation results

### With External Systems (via n8n)
- HRIS (e.g., BambooHR, Workday)
- IT Ticketing (e.g., Jira, ServiceNow)
- IAM (e.g., Okta, Azure AD)
- Email (e.g., Google Workspace, Microsoft 365)
- Asset Management

---

## Files Overview

| File | Purpose | Lines |
|------|---------|-------|
| `src/agent/provisioning.py` | Core agent logic | ~400 |
| `src/webhooks/n8n_client.py` | n8n webhook client | ~200 |
| `src/messaging/redis_client.py` | Redis stream client | ~150 |
| `src/api/routes.py` | REST API endpoints | ~100 |
| `src/config/settings.py` | Configuration | ~80 |
| `src/schemas/mcp_message.py` | Message schemas | ~100 |
| `src/main.py` | Entry point | ~80 |

**Total:** ~1,110 lines of Python code

---

## Conclusion

The Provisioning Agent is a **simple, deterministic, reliable** execution engine for provisioning tasks. Its design prioritizes:

- **Clarity** over cleverness
- **Reliability** over flexibility
- **Simplicity** over features

By offloading AI reasoning to the Orchestrator and external integrations to n8n, this agent does one thing well: **execute provisioning tasks reliably**.
