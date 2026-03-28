# Quick Test - Individual Workflow Tests

## Direct n8n Webhook Tests

### 1. Create HR Record
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-hr-record -H "Content-Type: application/json" -d "@test-payloads/test-webhook-hr.json"
```

### 2. Create IT Ticket
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-it-ticket -H "Content-Type: application/json" -d "@test-payloads/test-webhook-it-ticket.json"
```

### 3. Assign Access
```powershell
curl.exe -X POST http://localhost:5678/webhook/assign-access -H "Content-Type: application/json" -d "@test-payloads/test-webhook-access.json"
```

### 4. Generate Employee ID
```powershell
curl.exe -X POST http://localhost:5678/webhook/generate-employee-id -H "Content-Type: application/json" -d "@test-payloads/test-webhook-generate-id.json"
```

### 5. Create Email Account
```powershell
curl.exe -X POST http://localhost:5678/webhook/create-email -H "Content-Type: application/json" -d "@test-payloads/test-webhook-email.json"
```

### 6. Request Laptop
```powershell
curl.exe -X POST http://localhost:5678/webhook/request-laptop -H "Content-Type: application/json" -d "@test-payloads/test-webhook-laptop.json"
```

### 7. Schedule Induction
```powershell
curl.exe -X POST http://localhost:5678/webhook/schedule-induction -H "Content-Type: application/json" -d "@test-payloads/test-webhook-schedule.json"
```

### 8. Initiate Conversation
```powershell
curl.exe -X POST http://localhost:5678/webhook/initiate-conversation -H "Content-Type: application/json" -d "@test-payloads/test-webhook-conversation.json"
```

---

## Via Provisioning Agent API

### 1. Create HR Record
```powershell
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-hr-record.json"
```

### 2. Assign Access
```powershell
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-assign-access.json"
```

### 3. Generate Employee ID
```powershell
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-generate-id.json"
```

### 4. Create Email
```powershell
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-create-email.json"
```

### 5. Request Laptop
```powershell
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "@test-payloads/test-request-laptop.json"
```

---

## Via Orchestrator (Full Workflow)

```powershell
curl.exe -X POST http://localhost:8001/onboarding/initiate -H "Content-Type: application/json" -d "@test-payloads/test-onboarding.json"
```

---

## Run All Tests at Once

```powershell
.\test-all-8-workflows.ps1
```

---

## Expected Results

All tests should return:
- **Status**: `success`
- **Data**: Contains relevant IDs and timestamps
- **HTTP Status**: 200 OK

Check n8n executions at: http://localhost:5678 → Executions tab
