# Complete Workflow Testing Guide

## 📋 Overview
This guide will help you test all 8 n8n workflows in the AgenticHR system.

## 🎯 The 8 Workflows

### **Provisioning Agent Workflows (6)**
1. **Create HR Record** - Creates employee record in HRIS
2. **Create IT Ticket** - Creates ServiceNow ticket for IT setup
3. **Assign Access** - Grants role-based access (GitHub, AWS, Jira, etc.)
4. **Generate Employee ID** - Creates unique employee identifier with dept code
5. **Create Email** - Provisions email account in Exchange
6. **Request Laptop** - Submits laptop procurement request

### **Scheduler Agent Workflow (1)**
7. **Schedule Induction** - Creates calendar meeting for onboarding

### **Liaison Agent Workflow (1)**
8. **Initiate Conversation** - Sends welcome message to new employee

---

## 🚀 Quick Start - Run All Tests

```powershell
.\test-all-8-workflows.ps1
```

This will run **14 tests** in 3 sections:
- **Section A**: 8 direct n8n webhook tests
- **Section B**: 5 tests via Provisioning Agent API
- **Section C**: 1 complete Orchestrator workflow test

---

## 🔍 Individual Test Commands

### Test 1: Create HR Record
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-hr-record -H "Content-Type: application/json" -d "@test-payloads/test-webhook-hr.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "HR record created successfully",
  "data": {
    "record_id": "HR_1771907199998_rp6ojuez0",
    "employee_id": "EMP001",
    "system": "HRIS"
  }
}
```

### Test 2: Create IT Ticket
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-it-ticket -H "Content-Type: application/json" -d "@test-payloads/test-webhook-it-ticket.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "IT ticket created successfully",
  "data": {
    "ticket_id": "IT_1771907200714_wvug0e8v1",
    "priority": "HIGH",
    "system": "ServiceNow"
  }
}
```

### Test 3: Assign Access Roles
```powershell
curl.exe -X POST http://localhost:5678/webhook/assign-access -H "Content-Type: application/json" -d "@test-payloads/test-webhook-access.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Access granted for 3 role(s)",
  "data": {
    "assignment_id": "ACCESS_...",
    "total_roles": 3,
    "system": "IAM"
  }
}
```

### Test 4: Generate Employee ID
```powershell
curl.exe -X POST http://localhost:5678/webhook/generate-employee-id -H "Content-Type: application/json" -d "@test-payloads/test-webhook-generate-id.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Employee ID generated successfully",
  "data": {
    "employee_id": "MKT12345",
    "department_code": "MKT",
    "system": "ID_GENERATOR"
  }
}
```

### Test 5: Create Email Account
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-email -H "Content-Type: application/json" -d "@test-payloads/test-webhook-email.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Email account created successfully",
  "data": {
    "email_address": "eve.williams@acme.com",
    "mailbox_size_gb": 50,
    "system": "Exchange"
  }
}
```

### Test 6: Request Laptop
```powershell
curl.exe -X POST http://localhost:5678/webhook/request-laptop -H "Content-Type: application/json" -d "@test-payloads/test-webhook-laptop.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Laptop request submitted successfully",
  "data": {
    "request_id": "LAPTOP_...",
    "laptop_spec": "MacBook Pro 16 M3 Max, 32GB RAM, 1TB SSD",
    "delivery_days": 7,
    "system": "AssetManagement"
  }
}
```

### Test 7: Schedule Induction
```powershell
curl.exe -X POST http://localhost:5678/webhook/schedule-induction -H "Content-Type: application/json" -d "@test-payloads/test-webhook-schedule.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Induction meeting scheduled successfully",
  "data": {
    "meeting_id": "MEET_...",
    "title": "Onboarding Induction - Alice Johnson",
    "duration_minutes": 180,
    "attendees": [...],
    "calendar_system": "Google Calendar"
  }
}
```

### Test 8: Initiate Conversation
```powershell
curl.exe -X POST http://localhost:5678/webhook/initiate-conversation -H "Content-Type: application/json" -d "@test-payloads/test-webhook-conversation.json"
```
**Expected Output:**
```json
{
  "status": "success",
  "message": "Conversation initiated successfully",
  "data": {
    "conversation_id": "CONV_...",
    "welcome_message": "Hi Bob Smith! 👋...",
    "channel": "Email",
    "system": "Communication"
  }
}
```

---

## 🔄 Testing Via Provisioning Agent

Test the same workflows through the Provisioning Agent API:

```powershell
# Test 1: Create HR Record
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-hr-record.json"

# Test 2: Assign Access
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-assign-access.json"

# Test 3: Generate Employee ID
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-generate-id.json"

# Test 4: Create Email
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-create-email.json"

# Test 5: Request Laptop
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-request-laptop.json"
```

---

## 🎯 End-to-End Test (Complete Flow)

Test the entire workflow: **Orchestrator → Redis → Provisioning → n8n**

```powershell
curl.exe -X POST http://localhost:8001/onboarding/initiate -H "Content-Type: application/json" -d "@test-payloads/test-onboarding.json"
```

This will:
1. Create a workflow in Orchestrator
2. Generate tasks and send them to Redis
3. Provisioning Agent picks up tasks from Redis
4. Provisioning Agent calls n8n webhooks
5. n8n executes and returns results

---

## ✅ Verification Checklist

After running tests, verify:

### 1. Check n8n Executions
- Open http://localhost:5678
- Click **Executions** tab
- Verify all 8 workflows show green **Success** status

### 2. Check Provisioning Agent Logs
```powershell
# Check recent logs
Get-Content provisioning-agent\logs\provisioning.log -Tail 50
```

### 3. Check Redis Messages
```powershell
# Check pending messages
python orchestrator-agent\check_redis_messages.py
```

### 4. Check Orchestrator Workflows
```powershell
# Query workflow status
curl.exe http://localhost:8001/workflows/WF_acme_corp_EMP001_<id>/status
```

---

## 🐛 Troubleshooting

### Workflow Not Found (404)
**Problem**: Webhook returns 404
**Solution**: Make sure workflow is **Published** in n8n (green checkmark)

### Connection Refused
**Problem**: Cannot connect to n8n
**Solution**: Verify n8n is running
```powershell
docker ps | findstr n8n-cont
```

### Task Not Processing
**Problem**: Provisioning Agent not picking up tasks
**Solution**: Check Redis connection
```powershell
curl.exe http://localhost:8003/api/v1/health
# Should return: "redis_connected": true
```

### Invalid Payload
**Problem**: Workflow returns validation error
**Solution**: Check payload format matches expected structure

---

## 📊 Expected Results Summary

| Test # | Workflow | System | Key Output |
|--------|----------|--------|------------|
| 1 | Create HR Record | HRIS | `record_id: HR_...` |
| 2 | Create IT Ticket | ServiceNow | `ticket_id: IT_...` |
| 3 | Assign Access | IAM | `total_roles: N` |
| 4 | Generate Employee ID | ID_GENERATOR | `employee_id: DEPT12345` |
| 5 | Create Email | Exchange | `email_address: @acme.com` |
| 6 | Request Laptop | AssetManagement | `request_id: LAPTOP_...` |
| 7 | Schedule Induction | Google Calendar | `meeting_id: MEET_...` |
| 8 | Initiate Conversation | Communication | `conversation_id: CONV_...` |

---

## 🎓 Test Payload Files Created

All test files are in `C:\AgenticHR\test-payloads\`:

**Direct n8n webhook tests:**
- `test-webhook-hr.json`
- `test-webhook-it-ticket.json`
- `test-webhook-access.json`
- `test-webhook-generate-id.json`
- `test-webhook-email.json`
- `test-webhook-laptop.json`
- `test-webhook-schedule.json`
- `test-webhook-conversation.json`

**Provisioning Agent API tests:**
- `test-hr-record.json`
- `test-assign-access.json`
- `test-generate-id.json`
- `test-create-email.json`
- `test-request-laptop.json`

**Complete workflow test:**
- `test-onboarding.json`

---

## 🚀 Next Steps

1. ✅ Run the comprehensive test: `.\test-all-8-workflows.ps1`
2. ✅ Verify all 8 workflows in n8n Executions tab
3. ✅ Check logs for any errors
4. ✅ Test edge cases (invalid payloads, missing fields)
5. ✅ Ready for production!

---

**Happy Testing! 🎉**
