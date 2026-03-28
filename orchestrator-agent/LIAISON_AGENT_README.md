# Liaison Agent

The **Liaison Agent** is the conversational router and intent detection component of the AgenticHR multi-agent onboarding system.

## Overview

The Liaison Agent serves as the primary interface between users (new hires, HR staff, managers) and the multi-agent system. It handles natural language conversations, classifies user intents, and routes requests to appropriate specialized agents.

## Key Features

- **Intent Classification**: Automatically classifies user messages into:
  - `POLICY_QUERY`: Questions about company policies, leave, benefits, etc.
  - `TASK_REQUEST`: Action requests like leave applications, meeting scheduling
  - `APPROVAL_RESPONSE`: User responses to approval requests
  - `GENERAL_QUERY`: General questions or clarifications

- **Smart Routing**: Routes requests to appropriate agents:
  - Policy queries → Guide Agent (RAG-based policy retrieval)
  - Task requests → Orchestrator Agent (workflow management)
  - Approval responses → Orchestrator Agent (approval processing)

- **Context Management**: Maintains conversation history for multi-turn dialogues

- **Field Extraction**: Automatically extracts structured data from natural language:
  - Dates, durations, reasons
  - Employee names, emails
  - Urgency levels
  - Task-specific parameters

- **Clarification Handling**: Asks for missing information when needed

## Architecture

```
User Message
     ↓
Liaison Agent
     ├─→ Intent Classification (Gemini 2.5)
     ├─→ Field Extraction
     ├─→ Context Management
     └─→ Routing Decision
            ├─→ Guide Agent (Policy Queries)
            ├─→ Orchestrator Agent (Tasks & Approvals)
            └─→ User (Clarifications)
```

## Intent Classification Rules

### POLICY_QUERY
User asks about:
- Leave policies
- Company rules
- Holidays
- Benefits
- Working hours
- Internship policies

**Action**: Route to Guide Agent

### TASK_REQUEST
User requests:
- Apply for leave
- Schedule meeting
- Change joining date
- Request laptop/equipment
- Submit documents
- Any action requiring execution

**Action**: Delegate to Orchestrator Agent

### APPROVAL_RESPONSE
User says:
- "Yes" / "Approve"
- "No" / "Reject"
- "I confirm"
- "Proceed"

**Action**: Forward to Orchestrator Agent

### GENERAL_QUERY
Anything else requiring clarification or acknowledgment

**Action**: Ask for clarification or provide acknowledgment

## API Endpoints

### POST /message
Process incoming user message.

**Request**:
```json
{
  "message": "I want to apply for leave from March 15 to March 20",
  "tenant_id": "acme_corp",
  "user_id": "emp_12345",
  "workflow_id": "WF_optional",
  "user_name": "John Doe",
  "user_role": "employee",
  "metadata": {}
}
```

**Response**:
```json
{
  "response_text": "I'll process your leave request...",
  "intent_type": "TASK_REQUEST",
  "confidence_score": 0.95,
  "action_taken": "delegate_to_orchestrator",
  "workflow_id": "WF_acme_corp_emp12345_abc123",
  "requires_approval": false,
  "metadata": {},
  "timestamp": "2026-02-18T10:30:00Z"
}
```

### POST /approval
Process user's approval/rejection response.

**Request**:
```json
{
  "workflow_id": "WF_acme_corp_emp001_abc123",
  "tenant_id": "acme_corp",
  "user_id": "manager_001",
  "approval_status": "approved",
  "approver_note": "Approved for personal reasons",
  "timestamp": "2026-02-18T10:30:00Z"
}
```

### POST /guide-response
Receive response from Guide Agent (internal).

### POST /approval-request
Receive approval request from Orchestrator (internal).

### DELETE /conversation/{tenant_id}/{workflow_id}
Clear conversation history.

### GET /health
Health check endpoint.

## Communication Format

The Liaison Agent outputs **ONLY valid JSON** in the following format:

```json
{
  "action": "route_to_guide | delegate_to_orchestrator | ask_clarification | acknowledge",
  "workflow_id": "string or null",
  "tenant_id": "string",
  "intent_type": "POLICY_QUERY | TASK_REQUEST | APPROVAL_RESPONSE | GENERAL_QUERY",
  "confidence_score": 0.0-1.0,
  "payload": {
    "original_message": "user message",
    "structured_data": {
      "request_type": "leave_application",
      "dates": ["2026-03-15", "2026-03-20"],
      "reason": "personal work",
      "urgency_level": "medium"
    }
  },
  "reason": "brief reasoning",
  "user_response": "conversational response text"
}
```

## Field Extraction

### For Leave Applications:
- `request_type`: "leave_application"
- `start_date`: YYYY-MM-DD format
- `end_date`: YYYY-MM-DD format
- `duration`: number of days
- `reason`: text description
- `urgency_level`: low/medium/high

### For Meeting Scheduling:
- `request_type`: "meeting_schedule"
- `date`: YYYY-MM-DD format
- `time`: HH:MM format
- `attendees`: list of emails/names
- `duration`: in minutes
- `purpose`: meeting topic

### For Equipment Requests:
- `request_type`: "equipment_request"
- `equipment_type`: laptop/phone/monitor/etc
- `urgency_level`: low/medium/high
- `reason`: justification

## Setup and Running

### Prerequisites
- Python 3.10+
- Redis (for inter-agent communication)
- Google API Key (for Gemini 2.5)
- Environment variables configured

### Installation

1. Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

3. Start the Liaison Agent:
```bash
# Using PowerShell script
.\start_liaison.ps1

# Or directly with Python
python -m uvicorn src.api.liaison_main:app --host 0.0.0.0 --port 8002 --reload
```

### Testing

Run comprehensive tests:
```bash
python test_liaison.py
```

This will run 8 test cases covering:
1. Policy query classification
2. Task request classification
3. Approval response handling
4. Missing information detection
5. Multi-turn conversation context
6. MCP message creation
7. Guide response processing
8. Approval request formatting

## Integration with Other Agents

### With Guide Agent
```
User: "What is the leave policy?"
  ↓
Liaison Agent (classifies as POLICY_QUERY)
  ↓
→ MCP Message to Guide Agent
  ↓
Guide Agent retrieves policy from RAG
  ↓
← Response back to Liaison Agent
  ↓
Liaison Agent formats response
  ↓
User receives policy information
```

### With Orchestrator Agent
```
User: "I want to apply for leave from March 15-20"
  ↓
Liaison Agent (classifies as TASK_REQUEST)
  ↓
Extracts: start_date, end_date, request_type
  ↓
→ MCP Message to Orchestrator Agent
  ↓
Orchestrator creates workflow
  ↓
Delegates to Provisioning/Scheduler agents
  ↓
← Confirmation back to user
```

## Security Features

- **No data leakage**: Never exposes internal system architecture
- **Tenant isolation**: Strictly maintains tenant boundaries
- **No policy fabrication**: Only routes to Guide Agent for policies
- **Approval integrity**: Never fabricates approvals
- **Context privacy**: Conversation histories are isolated per tenant/workflow

## Behavior Constraints

1. **JSON-only output**: Never outputs plain text or markdown in routing decisions
2. **No hallucination**: Does not answer policy questions directly
3. **No direct execution**: Routes all tasks to appropriate agents
4. **Context awareness**: Maintains conversation history for better UX
5. **Clarification-first**: Asks for missing info rather than guessing

## Example Conversations

### Example 1: Policy Query
```
User: "What are the working hours for interns?"

Liaison Response:
{
  "action": "route_to_guide",
  "intent_type": "POLICY_QUERY",
  "confidence_score": 0.92,
  "user_response": "Let me check the policy information for you..."
}

→ Routed to Guide Agent
← Guide returns: "Interns work 9 AM to 5 PM, Monday to Friday..."
```

### Example 2: Leave Application
```
User: "I need leave for 3 days next week"

Liaison Response:
{
  "action": "ask_clarification",
  "intent_type": "TASK_REQUEST",
  "user_response": "Could you please specify the exact dates? (e.g., March 15 to March 17)"
}

User: "March 15 to March 17 for medical reasons"

Liaison Response:
{
  "action": "delegate_to_orchestrator",
  "intent_type": "TASK_REQUEST",
  "payload": {
    "structured_data": {
      "request_type": "leave_application",
      "start_date": "2026-03-15",
      "end_date": "2026-03-17",
      "reason": "medical reasons"
    }
  },
  "user_response": "I'll process your leave request..."
}
```

### Example 3: Approval Response
```
[Approval request sent to manager]

Manager: "Yes, approved"

Liaison Response:
{
  "action": "delegate_to_orchestrator",
  "intent_type": "APPROVAL_RESPONSE",
  "payload": {
    "structured_data": {
      "approval_status": "approved"
    }
  },
  "user_response": "Your decision to approved has been recorded. Thank you!"
}
```

## Logging

Logs are written to `logs/liaison.log` with rotation:
- Max size: 500 MB per file
- Retention: 10 days
- Format: `{timestamp} | {level} | {message}`

## Configuration

Key settings in `src/config/settings.py`:
- `liaison_agent_url`: Default http://localhost:8002
- `google_api_key`: Gemini API key
- `gemini_model`: Default "gemini-2.0-flash-exp"
- `redis_host`: Redis server host
- `redis_port`: Redis server port

## Troubleshooting

### Issue: "Invalid JSON from LLM"
- **Cause**: Gemini returned non-JSON response
- **Solution**: Check system prompt, ensure API key is valid

### Issue: "Missing required field"
- **Cause**: LLM didn't include all required fields
- **Solution**: Review system prompt formatting

### Issue: "Conversation context lost"
- **Cause**: Workflow ID not maintained across turns
- **Solution**: Ensure frontend sends workflow_id in subsequent messages

## Future Enhancements

- [ ] Multi-language support
- [ ] Voice input integration
- [ ] Sentiment analysis
- [ ] Proactive suggestions
- [ ] Analytics dashboard
- [ ] Custom entity extraction training

## License

Part of AgenticHR - Internal Use Only
