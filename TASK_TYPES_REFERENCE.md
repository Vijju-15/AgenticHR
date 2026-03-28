# Task Types Reference

This document provides a complete reference of all task types used across the AgenticHR multi-agent system.

## Overview

Task types are used in MCP messages to route tasks to the appropriate agent handlers. Each agent supports specific task types based on its domain responsibilities.

## Task Types by Agent

### Provisioning Agent (Port 8003)

Handles all user provisioning, access management, and IT infrastructure tasks.

| Task Type | Description | Required Payload Fields |
|-----------|-------------|------------------------|
| `create_hr_record` | Create employee record in HRIS system | `employee_name`, `employee_email`, `role`, `department` |
| `create_it_ticket` | Create IT helpdesk ticket for new hire | `employee_id`, `employee_name` |
| `assign_access` | Assign system/application access roles | `employee_id`, `access_roles` (array) |
| `generate_id` | Generate unique employee ID | `employee_name`, `department` |
| `create_email` | Provision corporate email account | `employee_name`, `department` |
| `request_laptop` | Request laptop/hardware for new hire | `employee_id`, `laptop_spec` |

### Scheduler Agent (Port TBD)

Handles all meeting scheduling and calendar management tasks.

| Task Type | Description | Required Payload Fields |
|-----------|-------------|------------------------|
| `schedule_induction` | Schedule onboarding induction session | `employee_email`, `employee_name`, `manager_email`, `start_date` |
| `schedule_meeting` | Schedule general meeting | `attendees`, `duration`, `subject` |

### Liaison Agent (Port 8002)

Handles all conversational interactions with new hires.

| Task Type | Description | Required Payload Fields |
|-----------|-------------|------------------------|
| `initiate_conversation` | Start conversation with new hire | `employee_name`, `employee_email`, `manager_email` |
| `send_message` | Send message to employee | `recipient_email`, `message` |

### Guide Agent (Port 8000)

Handles RAG-based policy and knowledge queries. No direct task delegation (called via Liaison).

## Task Type Naming Conventions

- Use snake_case for all task type identifiers
- Use verb-first naming: `create_`, `assign_`, `generate_`, `schedule_`, `send_`
- Keep names descriptive but concise (2-3 words)
- Avoid abbreviations unless widely recognized (e.g., `hr`, `it`)

## Common Pitfalls

### ❌ Incorrect Task Names (DO NOT USE)
- `create_hris_record` → Use `create_hr_record` instead
- `createHRRecord` → Use snake_case, not camelCase
- `hr_create` → Use verb-first: `create_hr_record`

### ✅ Correct Usage Examples

#### Orchestrator delegating to Provisioning Agent:
```json
{
  "action": "delegate_task",
  "target_agent": "provisioning_agent",
  "task": {
    "task_id": "TASK_abc123",
    "task_type": "create_hr_record",
    "payload": {
      "employee_name": "John Doe",
      "employee_email": "john.doe@acme.com",
      "role": "Software Engineer",
      "department": "Engineering"
    }
  }
}
```

#### Testing Provisioning Agent via Redis:
```bash
docker exec -it agentichr-redis redis-cli XADD agent_stream:provisioning_agent "*" message '{
  "message_id": "test_001",
  "workflow_id": "WF_test",
  "tenant_id": "acme",
  "from_agent": "orchestrator_agent",
  "to_agent": "provisioning_agent",
  "message_type": "task_request",
  "task": {
    "task_id": "task_001",
    "task_type": "create_hr_record",
    "payload": {
      "employee_name": "Test User",
      "employee_email": "test@acme.com",
      "role": "Engineer",
      "department": "IT"
    },
    "priority": 5,
    "retry_count": 0
  }
}'
```

## Version History

- **v1.0** (Initial) - Defined task types for Provisioning, Scheduler, Liaison agents
- **v1.1** (Current) - Fixed `create_hris_record` → `create_hr_record` consistency issue

## See Also

- [Orchestrator Implementation Summary](orchestrator-agent/IMPLEMENTATION_SUMMARY.md)
- [Provisioning Agent README](provisioning-agent/README.md)
- [Liaison Integration Guide](orchestrator-agent/LIAISON_INTEGRATION_GUIDE.md)
