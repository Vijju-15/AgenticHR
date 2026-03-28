# Testing the Liaison Agent

## Quick Test Checklist

### 1. Check if Agent is Running
```cmd
curl http://localhost:8002/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "agent": "liaison_agent",
  "version": "1.0.0"
}
```

Or open in browser: **http://localhost:8002/health**

---

### 2. View API Documentation
Open in browser: **http://localhost:8002/docs**

This shows all available endpoints with interactive testing.

---

### 3. Test with Simple Policy Query

**Using PowerShell:**
```powershell
$body = @{
    message = "What is the leave policy?"
    user_id = "test_user_001"
    tenant_id = "acme_corp"
    user_name = "Test User"
    user_role = "employee"
    metadata = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8002/message" -Method POST -Body $body -ContentType "application/json"
```

**Using curl:**
```bash
curl -X POST "http://localhost:8002/message" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"What is the leave policy?\",\"user_id\":\"test_user_001\",\"tenant_id\":\"acme_corp\",\"user_name\":\"Test User\",\"user_role\":\"employee\",\"metadata\":{}}"
```

**Expected Response:**
```json
{
  "response_text": "Let me check the policy information for you...",
  "intent_type": "policy_query",
  "confidence_score": 0.95,
  "action_taken": "route_to_guide",
  "workflow_id": "WF_acme_corp_test_user_001_xxxxx",
  "metadata": {
    "reason": "Policy query about leave",
    "payload": {...}
  }
}
```

---

### 4. Test with Task Request

**Using PowerShell:**
```powershell
$body = @{
    message = "I want to apply for leave from March 15 to March 20"
    user_id = "emp_12345"
    tenant_id = "acme_corp"
    user_name = "John Doe"
    user_role = "employee"
    metadata = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8002/message" -Method POST -Body $body -ContentType "application/json"
```

**Expected Response:**
```json
{
  "response_text": "I'll process your leave request and get back to you shortly.",
  "intent_type": "task_request",
  "confidence_score": 0.90,
  "action_taken": "delegate_to_orchestrator",
  "workflow_id": "WF_acme_corp_emp_12345_xxxxx",
  "metadata": {
    "reason": "Leave application request",
    "payload": {
      "structured_data": {
        "task_type": "leave_application",
        "start_date": "2026-03-15",
        "end_date": "2026-03-20"
      }
    }
  }
}
```

---

### 5. Test Approval Response

**Using PowerShell:**
```powershell
$body = @{
    user_id = "manager_001"
    tenant_id = "acme_corp"
    workflow_id = "WF_acme_corp_emp001_abc123"
    approval_status = "approved"
    approver_note = "Approved as requested"
    timestamp = (Get-Date).ToString("o")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8002/approval" -Method POST -Body $body -ContentType "application/json"
```

**Expected Response:**
```json
{
  "response_text": "Your decision to approved has been recorded. Thank you!",
  "intent_type": "approval_response",
  "confidence_score": 1.0,
  "action_taken": "delegate_to_orchestrator",
  "workflow_id": "WF_acme_corp_emp001_abc123",
  "metadata": {
    "approval_status": "approved"
  }
}
```

---

## Using the Interactive API Docs

1. **Start the agent** (if not running):
   ```cmd
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
   ```

2. **Open browser**: http://localhost:8002/docs

3. **Test POST /message endpoint**:
   - Click on `POST /message`
   - Click "Try it out"
   - Edit the request body:
   ```json
   {
     "message": "What is the leave policy?",
     "user_id": "test_user",
     "tenant_id": "acme_corp",
     "user_name": "Test User",
     "user_role": "employee",
     "metadata": {}
   }
   ```
   - Click "Execute"
   - See the response below

---

## Run Automated Tests

**Full test suite:**
```cmd
conda activate agenticHR
python test_liaison.py
```

**Tests included:**
1. ✅ Policy Query Classification
2. ✅ Task Request Classification
3. ✅ Approval Response Handling
4. ✅ Missing Information Detection
5. ✅ Multi-turn Conversation Context
6. ✅ MCP Message Creation
7. ✅ Guide Response Processing
8. ✅ Approval Request Formatting

**Expected output:**
```
====================================
TEST 1: Policy Query
====================================
...
✅ Test Passed: Policy query correctly classified and routed

====================================
TEST 2: Task Request - Leave Application
====================================
...
✅ Test Passed: Task request correctly classified and delegated

...

====================================
✅ ALL TESTS PASSED
====================================
```

---

## Test Different Intent Types

### 1. Policy Query
```json
{
  "message": "What are the working hours?",
  "user_id": "test_user",
  "tenant_id": "acme_corp",
  "user_name": "Test User",
  "user_role": "employee",
  "metadata": {}
}
```
**Expected**: `intent_type: "policy_query"`, `action_taken: "route_to_guide"`

### 2. Leave Application
```json
{
  "message": "I need leave from March 25 to March 30",
  "user_id": "emp_001",
  "tenant_id": "acme_corp",
  "user_name": "Employee One",
  "user_role": "employee",
  "metadata": {}
}
```
**Expected**: `intent_type: "task_request"`, `action_taken: "delegate_to_orchestrator"`

### 3. Meeting Request
```json
{
  "message": "Schedule a meeting with John tomorrow at 2 PM",
  "user_id": "emp_002",
  "tenant_id": "acme_corp",
  "user_name": "Employee Two",
  "user_role": "employee",
  "metadata": {}
}
```
**Expected**: `intent_type: "task_request"`, `action_taken: "delegate_to_orchestrator"`

### 4. General Query
```json
{
  "message": "Hello, how are you?",
  "user_id": "test_user",
  "tenant_id": "acme_corp",
  "user_name": "Test User",
  "user_role": "employee",
  "metadata": {}
}
```
**Expected**: `intent_type: "general_query"`, `action_taken: "acknowledge"`

---

## Check Logs

View detailed logs:
```cmd
type logs\liaison.log
```

Or tail logs in real-time (PowerShell):
```powershell
Get-Content logs\liaison.log -Wait -Tail 20
```

---

## Verify Setup

Run verification script:
```cmd
conda activate agenticHR
python verify_liaison.py
```

**Expected output:**
```
====================================
LIAISON AGENT - VERIFICATION SCRIPT
====================================

1. Checking Python version...
   ✅ Python version OK

2. Checking required files...
   ✅ src/agent/liaison.py
   ✅ src/api/main.py
   ...

3. Checking required dependencies...
   ✅ google-generativeai
   ✅ pydantic
   ...

4. Checking environment configuration...
   ✅ .env file found
   ✅ GOOGLE_API_KEY configured

...

✅ All core components verified successfully!
```

---

## Common Issues

### Agent returns error about missing data
- Check that all required fields are in request body
- Use the `/docs` endpoint to see exact schema

### Intent classification seems wrong
- Check logs: `type logs\liaison.log`
- Google API key might be invalid
- Test with automated tests: `python test_liaison.py`

### Connection refused
- Make sure agent is running: `http://localhost:8002/health`
- Check port 8002 is not blocked

### Redis errors (optional for testing)
- Redis is only needed for integration with other agents
- For standalone testing, Redis errors can be ignored

---

## Test Conversation Context

Test multi-turn conversation:

**Turn 1:**
```json
{
  "message": "I want to apply for leave",
  "user_id": "emp_001",
  "tenant_id": "acme_corp",
  "workflow_id": "WF_test_conversation",
  "user_name": "Test User",
  "user_role": "employee",
  "metadata": {}
}
```

**Turn 2 (same workflow_id):**
```json
{
  "message": "From March 15 to March 20",
  "user_id": "emp_001",
  "tenant_id": "acme_corp",
  "workflow_id": "WF_test_conversation",
  "user_name": "Test User",
  "user_role": "employee",
  "metadata": {}
}
```

The agent should remember the context from Turn 1.

---

## Success Indicators

✅ **Agent is working correctly if:**
- Health check returns `{"status": "healthy"}`
- `/message` endpoint returns proper intent classification
- Logs show no errors (except Redis warnings which are OK)
- Automated tests pass: `python test_liaison.py`
- API docs are accessible: http://localhost:8002/docs

---

## Next Steps

Once the Liaison Agent is tested:
1. Test integration with Guide Agent (if running)
2. Test integration with Orchestrator Agent (if running)
3. Set up Redis for inter-agent communication
4. Deploy to production environment

---

## Quick Reference

| What to Test | Command/URL |
|--------------|-------------|
| Health check | http://localhost:8002/health |
| API docs | http://localhost:8002/docs |
| Full test suite | `python test_liaison.py` |
| Verify setup | `python verify_liaison.py` |
| View logs | `type logs\liaison.log` |
| Test message | Use PowerShell/curl examples above |
