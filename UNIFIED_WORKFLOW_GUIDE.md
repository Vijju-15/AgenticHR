# Unified n8n Workflow - Setup & Testing Guide

## 🎯 What Changed?

### **Before (8 Separate Workflows):**
- 8 individual n8n workflows
- Each with its own webhook endpoint
- Difficult to manage and maintain
- No centralized routing logic

### **After (1 Unified Workflow):**
- **Single workflow** with intelligent routing
- Uses n8n's **Switch node** for task type branching
- **Merge node** to combine all outputs
- Centralized error handling
- Much better use of n8n features!

---

## 🏗️ Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Unified Provisioning Workflow                   │
└─────────────────────────────────────────────────────────────────┘

Webhook Trigger (/webhook/provisioning)
         │
         │ Receives: { "task_type": "...", "payload": {...} }
         │
         ▼
   Switch Node (Route by Task Type)
         │
         ├──► create_hr_record     ──┐
         ├──► create_it_ticket      ──┤
         ├──► assign_access         ──┤
         ├──► generate_id           ──┤
         ├──► create_email          ──├──► Merge Node
         ├──► request_laptop        ──┤
         ├──► schedule_induction    ──┤
         ├──► initiate_conversation ──┤
         └──► unknown (error)       ──┘
                                       │
                                       ▼
                              Respond to Webhook
```

---

## 📦 Installation Steps

### **1. Import Workflow into n8n**

```powershell
# Workflow file location
C:\AgenticHR\n8n\provisioning\unified-provisioning-workflow.json
```

**In n8n UI:**
1. Open n8n: http://localhost:5678
2. Click **"+"** → **"Import from File"**
3. Select `unified-provisioning-workflow.json`
4. Click **"Import"**

### **2. Publish the Workflow**

1. Review the workflow nodes
2. Click **"Publish"** button (top right)
3. Confirm workflow is active (green checkmark)

### **3. Deactivate Old Workflows** (Optional)

You can now unpublish the 8 individual workflows:
- create-hr-record
- create-it-ticket
- assign-access
- generate-employee-id
- create-email
- request-laptop
- schedule-induction
- initiate-conversation

---

## 🧪 Testing the Unified Workflow

### **Test 1: Create HR Record**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-hr-record.json"
```

**Expected Response:**
```json
{
  "status": "success",
  "task_type": "create_hr_record",
  "message": "HR record created successfully",
  "data": {
    "record_id": "HR_...",
    "employee_name": "Alice Johnson",
    "system": "HRIS"
  }
}
```

### **Test 2: Create IT Ticket**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-it-ticket.json"
```

### **Test 3: Assign Access**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-assign-access.json"
```

### **Test 4: Generate Employee ID**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-generate-id.json"
```

### **Test 5: Create Email**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-create-email.json"
```

### **Test 6: Request Laptop**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-request-laptop.json"
```

### **Test 7: Schedule Induction**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-schedule-induction.json"
```

### **Test 8: Initiate Conversation**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-initiate-conversation.json"
```

### **Test 9: Error Handling (Unknown Task)**
```powershell
curl.exe -X POST http://localhost:5678/webhook/provisioning `
  -H "Content-Type: application/json" `
  -d "@test-payloads/unified/test-error-handling.json"
```

**Expected Error Response:**
```json
{
  "status": "error",
  "task_type": "unknown_task",
  "message": "Unknown task type",
  "error": {
    "code": "UNKNOWN_TASK_TYPE",
    "details": "Task type 'unknown_task' is not supported",
    "supported_types": [...]
  }
}
```

---

## 🔄 Restart Provisioning Agent

The agent has been updated to use the unified webhook:

```powershell
# Stop current agent (if running)
# Press Ctrl+C in the agent terminal

# Restart with conda environment
cmd /k "C:/ProgramData/Anaconda3/Scripts/activate && conda activate agenticHR && cd C:\AgenticHR\provisioning-agent && python -m uvicorn src.main:app --host 0.0.0.0 --port 8003"
```

---

## 🎯 Key n8n Features Used

### **1. Switch Node (Flow Control)**
- Routes based on `task_type` field
- 8 different output branches
- Fallback output for errors

### **2. Function Nodes (Data Transformation)**
- Each task type has its own processing logic
- Generates unique IDs
- Formats response data

### **3. Merge Node (Data Flow)**
- Combines outputs from all branches
- Ensures single response path

### **4. Respond to Webhook (Core)**
- Dynamic status code based on success/error
- Custom headers (X-Task-Type)
- JSON response formatting

### **5. Error Handling**
- Unknown task types handled gracefully
- Returns helpful error messages
- Lists supported task types

---

## 📊 Comparison: Old vs New

| Feature | 8 Separate Workflows | 1 Unified Workflow |
|---------|---------------------|-------------------|
| **n8n Workflows** | 8 | 1 |
| **Webhook Endpoints** | 8 | 1 |
| **Management Complexity** | High | Low |
| **Code Duplication** | High | None |
| **Flow Control** | None | Switch + Merge |
| **Error Handling** | Per workflow | Centralized |
| **Maintenance** | Difficult | Easy |
| **Scalability** | Poor | Excellent |
| **Uses n8n Features** | ❌ Basic | ✅ Advanced |

---

## 🚀 Complete Test Script

Save this as `test-unified-workflow.ps1`:

```powershell
# Test Unified n8n Workflow

Write-Host "`nTesting Unified Provisioning Workflow`n" -ForegroundColor Cyan

$tests = @(
    @{ Name = "Create HR Record"; File = "test-hr-record.json" },
    @{ Name = "Create IT Ticket"; File = "test-it-ticket.json" },
    @{ Name = "Assign Access"; File = "test-assign-access.json" },
    @{ Name = "Generate Employee ID"; File = "test-generate-id.json" },
    @{ Name = "Create Email"; File = "test-create-email.json" },
    @{ Name = "Request Laptop"; File = "test-request-laptop.json" },
    @{ Name = "Schedule Induction"; File = "test-schedule-induction.json" },
    @{ Name = "Initiate Conversation"; File = "test-initiate-conversation.json" },
    @{ Name = "Error Handling"; File = "test-error-handling.json" }
)

$testNum = 1
foreach ($test in $tests) {
    Write-Host "Test $testNum: $($test.Name)" -ForegroundColor Yellow
    curl.exe -X POST http://localhost:5678/webhook/provisioning `
      -H "Content-Type: application/json" `
      -d "@test-payloads/unified/$($test.File)"
    Write-Host "`n---`n"
    $testNum++
    Start-Sleep -Milliseconds 300
}

Write-Host "All tests complete!`n" -ForegroundColor Green
```

---

## ✅ Advantages of Unified Workflow

1. **Single Point of Entry**: One webhook endpoint for all tasks
2. **Centralized Routing**: Switch node handles all logic
3. **Easy Maintenance**: Update one workflow instead of 8
4. **Better Monitoring**: All executions in one place
5. **Scalability**: Easy to add new task types
6. **Error Handling**: Centralized error responses
7. **Better n8n Usage**: Leverages flow control features
8. **Reduced Complexity**: Less to manage and deploy

---

## 🎓 Next Steps

1. Import unified workflow into n8n
2. Publish the workflow
3. Restart Provisioning Agent
4. Run test script
5. Deactivate old workflows (optional)
6. Monitor executions in n8n UI

---

**You're now using n8n like a pro!** 🚀
