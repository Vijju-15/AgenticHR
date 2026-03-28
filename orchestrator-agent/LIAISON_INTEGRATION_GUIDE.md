# Liaison Agent - Integration Guide

This guide explains how the Liaison Agent integrates with other agents in the AgenticHR system.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AgenticHR System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User (Employee/Manager/HR)                                 │
│           ↓                                                 │
│  ┌──────────────────┐                                       │
│  │  Liaison Agent   │  ← You are here                       │
│  │  (Port 8002)     │                                       │
│  └────────┬─────────┘                                       │
│           │                                                 │
│    ┌──────┴──────┬──────────┬──────────┐                   │
│    ↓             ↓          ↓          ↓                    │
│  ┌────────┐  ┌─────────┐ ┌────────┐ ┌──────────┐           │
│  │ Guide  │  │Orchestr.│ │Provis. │ │Scheduler │           │
│  │ Agent  │  │ Agent   │ │ Agent  │ │  Agent   │           │
│  │(8000)  │  │ (8001)  │ │ (8003) │ │  (8004)  │           │
│  └────────┘  └─────────┘ └────────┘ └──────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓
      Redis Streams         MongoDB
```

## Communication Flow

### 1. Policy Query Flow

```
User → Liaison Agent → Guide Agent → Liaison Agent → User
```

**Step-by-step:**

1. **User sends message:**
   ```
   POST /message
   {
     "message": "What is the leave policy?",
     "tenant_id": "acme_corp",
     "user_id": "emp_001"
   }
   ```

2. **Liaison classifies intent:**
   - Intent: POLICY_QUERY
   - Confidence: 0.95
   - Action: route_to_guide

3. **Liaison creates MCP message:**
   ```json
   {
     "message_id": "MSG_abc123...",
     "workflow_id": "WF_acme_corp_...",
     "tenant_id": "acme_corp",
     "from_agent": "liaison_agent",
     "to_agent": "guide_agent",
     "message_type": "query",
     "data": {
       "original_message": "What is the leave policy?",
       "query_topic": "leave_policy",
       "keywords": ["leave", "policy"]
     }
   }
   ```

4. **Message sent to Redis Stream:**
   - Stream: `agent_stream:guide_agent`
   - Consumer Group: `guide_agent_group`

5. **Guide Agent processes query:**
   - Retrieves from RAG (Qdrant + knowledge base)
   - Returns policy information

6. **Guide Agent sends response:**
   ```
   POST /guide-response
   {
     "tenant_id": "acme_corp",
     "workflow_id": "WF_acme_corp_...",
     "query": "What is the leave policy?",
     "response": "According to the leave policy..."
   }
   ```

7. **Liaison formats and returns to user:**
   ```json
   {
     "response_text": "According to the leave policy...",
     "intent_type": "POLICY_QUERY",
     "confidence_score": 1.0,
     "action_taken": "acknowledge"
   }
   ```

### 2. Task Request Flow

```
User → Liaison Agent → Orchestrator Agent → [Provisioning/Scheduler] → User
```

**Step-by-step:**

1. **User sends task request:**
   ```
   POST /message
   {
     "message": "I want to apply for leave from March 15 to March 20",
     "tenant_id": "acme_corp",
     "user_id": "emp_001",
     "user_name": "John Doe"
   }
   ```

2. **Liaison classifies and extracts:**
   - Intent: TASK_REQUEST
   - Structured data:
     ```json
     {
       "request_type": "leave_application",
       "start_date": "2026-03-15",
       "end_date": "2026-03-20",
       "duration": 6,
       "employee_name": "John Doe",
       "urgency_level": "medium"
     }
     ```

3. **Liaison creates MCP message for Orchestrator:**
   ```json
   {
     "message_id": "MSG_def456...",
     "workflow_id": "WF_acme_corp_emp001_xyz",
     "tenant_id": "acme_corp",
     "from_agent": "liaison_agent",
     "to_agent": "orchestrator_agent",
     "message_type": "task_request",
     "data": {
       "original_message": "I want to apply for leave...",
       "structured_data": {
         "request_type": "leave_application",
         "start_date": "2026-03-15",
         "end_date": "2026-03-20"
       }
     }
   }
   ```

4. **Orchestrator receives and plans workflow:**
   - Creates workflow in MongoDB
   - Plans task breakdown:
     - Task 1: Validate leave balance (Provisioning)
     - Task 2: Check calendar conflicts (Scheduler)
     - Task 3: Request manager approval (Liaison)

5. **Orchestrator delegates tasks:**
   - Sends MCP messages to Provisioning, Scheduler agents
   - Updates workflow state

6. **If approval needed:**
   ```
   POST /approval-request (to Liaison)
   {
     "tenant_id": "acme_corp",
     "workflow_id": "WF_acme_corp_emp001_xyz",
     "task_type": "leave_application",
     "details": {
       "employee": "John Doe",
       "start_date": "2026-03-15",
       "end_date": "2026-03-20"
     }
   }
   ```

7. **Liaison formats approval request for manager:**
   ```json
   {
     "response_text": "Leave application request:\n- Employee: John Doe\n- From: 2026-03-15\n- To: 2026-03-20\n\nDo you approve?",
     "intent_type": "APPROVAL_RESPONSE",
     "requires_approval": true
   }
   ```

### 3. Approval Response Flow

```
Manager → Liaison Agent → Orchestrator Agent → Workflow Update
```

**Step-by-step:**

1. **Manager responds:**
   ```
   POST /approval
   {
     "workflow_id": "WF_acme_corp_emp001_xyz",
     "tenant_id": "acme_corp",
     "user_id": "manager_001",
     "approval_status": "approved",
     "approver_note": "Approved"
   }
   ```

2. **Liaison creates structured response:**
   ```json
   {
     "action": "delegate_to_orchestrator",
     "intent_type": "APPROVAL_RESPONSE",
     "payload": {
       "structured_data": {
         "approval_status": "approved",
         "approver_id": "manager_001",
         "approver_note": "Approved"
       }
     }
   }
   ```

3. **Liaison sends MCP message to Orchestrator:**
   ```json
   {
     "message_type": "task_request",
     "to_agent": "orchestrator_agent",
     "data": {
       "approval_status": "approved"
     }
   }
   ```

4. **Orchestrator updates workflow:**
   - Updates state to ACTIVE
   - Continues with next tasks
   - Notifies employee

## Redis Streams Integration

### Stream Names
- `agent_stream:liaison_agent` - Messages for Liaison
- `agent_stream:guide_agent` - Messages for Guide
- `agent_stream:orchestrator_agent` - Messages for Orchestrator
- `agent_stream:provisioning_agent` - Messages for Provisioning
- `agent_stream:scheduler_agent` - Messages for Scheduler

### Consumer Groups
Each agent has a consumer group:
- `liaison_agent_group`
- `guide_agent_group`
- `orchestrator_agent_group`
- etc.

### Publishing Messages

```python
from src.messaging.redis_client import redis_client
from src.agent.liaison import liaison_agent
from src.schemas.mcp_message import AgentType, MessageType

# Create routing result
routing_result = liaison_agent.process_message(...)

# Create MCP message
mcp_message = liaison_agent.create_mcp_message(
    routing_result=routing_result,
    to_agent=AgentType.GUIDE,
    message_type=MessageType.QUERY
)

# Publish to Redis
redis_client.publish_message(mcp_message)
```

### Reading Messages

```python
# Read messages from liaison's stream
messages = redis_client.read_messages(
    agent_name="liaison_agent",
    count=10,
    block=1000  # Block for 1 second
)

# Process each message
for msg_id, msg_data in messages:
    mcp_message = MCPMessage(**json.loads(msg_data["message"]))
    # Process the message
```

## API Integration Examples

### Example 1: Frontend Integration

```javascript
// Send user message to Liaison Agent
async function sendMessage(message, tenantId, userId) {
  const response = await fetch('http://localhost:8002/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      tenant_id: tenantId,
      user_id: userId,
      user_name: "John Doe",
      user_role: "employee"
    })
  });
  
  const result = await response.json();
  console.log('Response:', result.response_text);
  console.log('Intent:', result.intent_type);
  console.log('Workflow ID:', result.workflow_id);
  
  return result;
}

// Handle approval request
async function sendApproval(workflowId, tenantId, userId, decision) {
  const response = await fetch('http://localhost:8002/approval', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      workflow_id: workflowId,
      tenant_id: tenantId,
      user_id: userId,
      approval_status: decision, // "approved" or "rejected"
      approver_note: "Looks good"
    })
  });
  
  return await response.json();
}
```

### Example 2: Testing with cURL

```bash
# Send a policy query
curl -X POST http://localhost:8002/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the leave policy?",
    "tenant_id": "acme_corp",
    "user_id": "emp_001"
  }'

# Send a leave application request
curl -X POST http://localhost:8002/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to apply for leave from March 15 to March 20",
    "tenant_id": "acme_corp",
    "user_id": "emp_001",
    "user_name": "John Doe"
  }'

# Send approval response
curl -X POST http://localhost:8002/approval \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "WF_acme_corp_emp001_abc123",
    "tenant_id": "acme_corp",
    "user_id": "manager_001",
    "approval_status": "approved"
  }'

# Health check
curl http://localhost:8002/health
```

### Example 3: Python Client

```python
import requests

# Initialize client
BASE_URL = "http://localhost:8002"

def send_message(message, tenant_id, user_id):
    """Send message to Liaison Agent."""
    response = requests.post(
        f"{BASE_URL}/message",
        json={
            "message": message,
            "tenant_id": tenant_id,
            "user_id": user_id
        }
    )
    return response.json()

def send_approval(workflow_id, tenant_id, user_id, status):
    """Send approval response."""
    response = requests.post(
        f"{BASE_URL}/approval",
        json={
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "approval_status": status
        }
    )
    return response.json()

# Example usage
if __name__ == "__main__":
    # Ask about policy
    result = send_message(
        message="What is the leave policy?",
        tenant_id="acme_corp",
        user_id="emp_001"
    )
    print(f"Response: {result['response_text']}")
    print(f"Intent: {result['intent_type']}")
    
    # Apply for leave
    result = send_message(
        message="I want to apply for leave from March 15-20",
        tenant_id="acme_corp",
        user_id="emp_001"
    )
    workflow_id = result['workflow_id']
    print(f"Workflow ID: {workflow_id}")
    
    # Approve (as manager)
    approval = send_approval(
        workflow_id=workflow_id,
        tenant_id="acme_corp",
        user_id="manager_001",
        status="approved"
    )
    print(f"Approval: {approval['response_text']}")
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  (Web App / Mobile App / Slack / Teams / Email)              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
          ┌──────────────────────────────┐
          │     Liaison Agent (8002)     │
          │  - Intent Classification     │
          │  - Field Extraction          │
          │  - Routing Logic             │
          └──────────┬───────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ↓            ↓            ↓
   ┌────────┐  ┌──────────┐  ┌────────┐
   │ Guide  │  │Orchestr. │  │ Redis  │
   │ Agent  │  │  Agent   │  │Streams │
   │(8000)  │  │  (8001)  │  │        │
   └───┬────┘  └────┬─────┘  └────┬───┘
       │            │              │
       ↓            ↓              ↓
   ┌────────┐  ┌──────────┐  ┌────────┐
   │Qdrant  │  │ MongoDB  │  │Provis. │
   │  RAG   │  │Workflows │  │Schedul.│
   └────────┘  └──────────┘  └────────┘
```

## Complete Example Scenario

### Scenario: New Hire Leave Application

1. **New hire asks about policy:**
   ```
   User: "How many leaves do I get?"
   → Liaison: POLICY_QUERY → Guide Agent
   ← Guide: "You get 15 days after 6 months"
   ← Liaison: Returns policy to user
   ```

2. **User applies for leave:**
   ```
   User: "I want leave from March 15-17"
   → Liaison: TASK_REQUEST (extracts dates)
   → Orchestrator: Creates workflow
   → Provisioning: Checks leave balance
   → Scheduler: Checks calendar conflicts
   ```

3. **Approval needed:**
   ```
   ← Orchestrator: Approval request
   ← Liaison: Formats for manager
   Manager: "Approved"
   → Liaison: Processes approval
   → Orchestrator: Updates workflow
   → Provisioning: Updates HRIS
   → Scheduler: Blocks calendar
   ```

4. **Completion:**
   ```
   ← Orchestrator: Workflow complete
   ← Liaison: Notifies user
   User: Receives confirmation
   ```

## Error Handling

### Error Flow

```
User → Liaison → [Error] → Liaison → User
                    ↓
              [Log Error]
                    ↓
              [Return Safe Response]
```

### Example Error Responses

```json
{
  "action": "ask_clarification",
  "intent_type": "GENERAL_QUERY",
  "confidence_score": 0.0,
  "user_response": "I apologize, but I encountered an error. Could you please rephrase?",
  "payload": {
    "error": "Error message"
  }
}
```

## Monitoring and Logging

### Log Locations
- Liaison Agent: `logs/liaison.log`
- Orchestrator Agent: `logs/orchestrator.log`
- Redis messages: `logs/redis_messages.log`

### Key Metrics to Monitor
- Intent classification accuracy
- Response times
- Message routing success rate
- Conversation completion rate
- Error rates by type

## Deployment Checklist

- [ ] Redis server running
- [ ] MongoDB running
- [ ] Environment variables configured
- [ ] All agents started in order:
  1. Start Redis
  2. Start MongoDB
  3. Start Guide Agent (8000)
  4. Start Orchestrator Agent (8001)
  5. Start Liaison Agent (8002)
  6. Start Provisioning Agent (8003)
  7. Start Scheduler Agent (8004)
- [ ] Health checks passing for all agents
- [ ] Test message flow end-to-end

## Troubleshooting

### Issue: Messages not routed
- Check Redis connection
- Verify stream names match
- Check consumer groups are created

### Issue: Intent misclassification
- Review and adjust system prompt
- Check confidence scores
- Add more examples if needed

### Issue: Missing structured data
- Check field extraction logic
- Verify LLM response format
- Add validation rules

## Next Steps

1. Read [LIAISON_AGENT_README.md](LIAISON_AGENT_README.md) for detailed API documentation
2. Run `python verify_liaison.py` to check setup
3. Run `python test_liaison.py` to test functionality
4. Start agent with `.\start_liaison.ps1`
5. Test integration with other agents

## Support

For issues or questions:
- Check logs in `logs/liaison.log`
- Review conversation history
- Test with `test_liaison.py`
- Verify Redis and MongoDB connectivity
