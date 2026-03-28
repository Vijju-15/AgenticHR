# n8n Workflows for AgenticHR

This directory contains all n8n workflow JSON files for the AgenticHR platform.

## Directory Structure

```
n8n/
├── provisioning/
│   ├── employee-setup-workflow.json      ← ✅ NEW  /employee-setup  (6 task types)
│   ├── master-onboarding-workflow.json   ← ✅ NEW  /onboarding-trigger (full pipeline)
│   ├── unified-provisioning-workflow.json (legacy — kept for reference)
│   ├── create-hr-record.json             (legacy individual workflows)
│   ├── create-it-ticket.json
│   ├── assign-access.json
│   ├── generate-employee-id.json
│   ├── create-email.json
│   └── request-laptop.json
├── scheduler/
│   └── schedule-induction.json          ← /schedule-induction
├── liaison/
│   ├── leave-notification-workflow.json  ← ✅ NEW  /leave-notification
│   └── initiate-conversation.json        ← /initiate-conversation
└── README.md
```

## Active Webhook Endpoints (import these)

| Priority | File | Webhook Path | Called by |
|----------|------|-------------|-----------|
| ⭐ Critical | `provisioning/employee-setup-workflow.json` | `/webhook/employee-setup` | Provisioning Agent |
| ⭐ Critical | `provisioning/master-onboarding-workflow.json` | `/webhook/onboarding-trigger` | External / HR systems |
| ⭐ Critical | `liaison/leave-notification-workflow.json` | `/webhook/leave-notification` | Orchestrator Agent (auto) |
| Legacy | `scheduler/schedule-induction.json` | `/webhook/schedule-induction` | Scheduler Agent |
| Legacy | `liaison/initiate-conversation.json` | `/webhook/initiate-conversation` | Liaison Agent |

---

## How to Import Workflows

### Step 1: Start n8n

```powershell
docker start n8n-cont
# Open browser: http://localhost:5678
```

### Step 2: Import Each Workflow

For each JSON file:
1. Open n8n at `http://localhost:5678`
2. Click **"+ Add workflow"** → three-dot menu → **Import from File**
3. Select the JSON file → **Open** → **Save** → **Activate**

### Step 3: Verify Webhook URLs

After activating, confirm these paths respond:

```powershell
# Employee Setup (replaces /provisioning)
Invoke-WebRequest http://localhost:5678/webhook/employee-setup -Method POST `
  -ContentType 'application/json' `
  -Body '{"task_type":"generate_employee_id","tenant_id":"acme","payload":{"employee_name":"Jane Doe","department":"Engineering"}}'

# Master Onboarding Trigger
Invoke-WebRequest http://localhost:5678/webhook/onboarding-trigger -Method POST `
  -ContentType 'application/json' `
  -Body '{"employee_name":"Jane Doe","employee_email":"jane@acme.com","role":"Engineer","department":"Engineering","start_date":"2026-03-10","tenant_id":"acme_corp"}'

# Leave Notification
Invoke-WebRequest http://localhost:5678/webhook/leave-notification -Method POST `
  -ContentType 'application/json' `
  -Body '{"request_id":"LR_001","employee_name":"Jane","employee_email":"jane@acme.com","leave_type":"annual","start_date":"2026-03-15","end_date":"2026-03-17","num_days":3,"decision":"APPROVED","tenant_id":"acme_corp"}'
```

---

## Workflow Details

### 1. `/webhook/employee-setup` — Employee Setup Workflow
Replaces the old `/provisioning` endpoint. Called by `provisioning-agent/src/agent/provisioning.py`.

**Supported `task_type` values:**

| task_type | What it does |
|-----------|-------------|
| `create_employee_record` | Registers employee in HRIS, returns `employee_id` + `record_url` |
| `generate_employee_id` | Generates `DEPT+YEAR+XXXX` formatted ID |
| `assign_department` | Assigns department, role, manager |
| `send_welcome_credentials` | Composes welcome email with temp password *(wire Gmail node for real sending)* |
| `initialize_onboarding` | Creates 3-day journey structure |
| `create_onboarding_checklist` | Builds Day-1/2/3 checklist |

**To send real welcome emails:** replace the `Send Email (Mock)` Code node with an n8n **Gmail** or **Send Email (SMTP)** node.

---

### 2. `/webhook/onboarding-trigger` — Master Onboarding Pipeline
Single external entry point that starts the full onboarding pipeline.

**Flow:** Webhook → Validate payload → `POST http://localhost:8001/onboarding/initiate` → Return workflow status

**Required payload fields:**
```json
{
  "employee_name":  "Jane Doe",
  "employee_email": "jane@acme.com",
  "role":           "Software Engineer",
  "department":     "Engineering",
  "start_date":     "2026-03-10",
  "tenant_id":      "acme_corp",
  "manager_email":  "manager@acme.com"
}
```

After firing, the Python Orchestrator Agent takes over and delegates:
employee_id generation → employee record → department → credentials → 3-day journey → meeting → welcome conversation.

---

### 3. `/webhook/leave-notification` — Leave Decision Notification
Automatically called by `orchestrator-agent/src/main.py` as a **background task** whenever HR approves or rejects a leave request.

**To send real email:** In n8n, replace the `Send Email (Mock)` Code node with a **Gmail** node wired to:
- `To`: `{{ $('Compose Leave Notification').first().json.to_email }}`
- `Subject`: `{{ $('Compose Leave Notification').first().json.subject }}`
- `Message`: `{{ $('Compose Leave Notification').first().json.body_text }}`

---

## Full Platform Architecture

```
External HR System / Frontend
        │
        ▼
n8n: /webhook/onboarding-trigger
        │
        ▼
Orchestrator Agent :8001  ──── MongoDB (workflows, tasks, leave_requests, onboarding_journeys, users)
   │        │        │
   ▼        ▼        ▼
Employee  Scheduler  Liaison
Setup     Agent      Agent
Agent     :8004      :8002
:8003       │           │
   │        │           ▼
   ▼        │        Guide Agent :8000
n8n:        │           │
/employee-  │           ▼
  setup     │        Qdrant RAG + Gemini
            │
            ▼
        n8n: /webhook/schedule-induction

Leave Decision Flow:
  HR Frontend → POST /leave/requests/{id}/decision
              → Orchestrator updates MongoDB
              → Background task → n8n: /webhook/leave-notification
              → Employee receives email
```

#### Liaison Agent (Port 8002)
- ✅ http://localhost:5678/webhook/initiate-conversation

## Testing Workflows

### Test Individual Webhook

From PowerShell:

```powershell
# Test Create HR Record
curl.exe -X POST http://localhost:5678/webhook/create-hr-record -H "Content-Type: application/json" -d "{\"employee_name\":\"Test User\",\"employee_email\":\"test@acme.com\",\"role\":\"Engineer\",\"department\":\"IT\"}"

# Test Create IT Ticket
curl.exe -X POST http://localhost:5678/webhook/create-it-ticket -H "Content-Type: application/json" -d "{\"employee_id\":\"EMP001\",\"employee_name\":\"Test User\",\"required_systems\":[\"email\",\"vpn\"]}"

# Test Schedule Induction
curl.exe -X POST http://localhost:5678/webhook/schedule-induction -H "Content-Type: application/json" -d "{\"employee_name\":\"Test User\",\"employee_email\":\"test@acme.com\",\"manager_email\":\"manager@acme.com\",\"start_date\":\"2026-03-01\"}"
```

### Test via Agent API

```powershell
# Test Provisioning Agent → n8n
curl.exe -X POST http://localhost:8003/api/v1/execute-task -H "Content-Type: application/json" -d "{\"workflow_id\":\"WF_test_001\",\"tenant_id\":\"acme_corp\",\"task\":{\"task_id\":\"TASK_HR_001\",\"task_type\":\"create_hr_record\",\"payload\":{\"employee_name\":\"Bob Smith\",\"employee_email\":\"bob@acme.com\",\"role\":\"Engineer\",\"department\":\"IT\"},\"priority\":5,\"retry_count\":0}}"
```

### Test via Orchestrator (Full Workflow)

```powershell
# Initiate complete onboarding workflow
curl.exe -X POST http://localhost:8001/onboarding/initiate -H "Content-Type: application/json" -d "{\"tenant_id\":\"acme_corp\",\"employee_id\":\"EMP001\",\"employee_name\":\"Alice Johnson\",\"employee_email\":\"alice@acme.com\",\"role\":\"Software Engineer\",\"department\":\"Engineering\",\"start_date\":\"2026-03-01\",\"manager_email\":\"manager@acme.com\"}"
```

## Workflow Features

All workflows include:

✅ **Webhook Trigger** - POST endpoint with custom path  
✅ **Request Logging** - Console logs for debugging  
✅ **Data Processing** - Business logic simulation  
✅ **Response Generation** - Structured JSON responses  
✅ **Error Handling** - Proper HTTP status codes  

## Monitoring Workflows

### View Execution History

1. Go to http://localhost:5678
2. Click **Executions** (left sidebar)
3. See all webhook calls and their results

### Debug Failed Executions

1. Click on a failed execution
2. See error details and input data
3. Edit workflow and re-test

## Quick Import Script

Run this PowerShell script to test all webhooks work:

```powershell
# Test all Provisioning Agent webhooks
$workflows = @(
    @{path="create-hr-record"; data='{"employee_name":"Test","employee_email":"test@acme.com","role":"Engineer","department":"IT"}'},
    @{path="create-it-ticket"; data='{"employee_id":"EMP001","employee_name":"Test","required_systems":["email"]}'},
    @{path="assign-access"; data='{"employee_id":"EMP001","access_roles":["github"]}'},
    @{path="generate-employee-id"; data='{"employee_name":"Test","department":"IT"}'},
    @{path="create-email"; data='{"employee_name":"Test","department":"IT"}'},
    @{path="request-laptop"; data='{"employee_id":"EMP001","laptop_spec":"MacBook Pro"}'}
)

foreach ($wf in $workflows) {
    Write-Host "Testing $($wf.path)..." -ForegroundColor Cyan
    curl.exe -X POST "http://localhost:5678/webhook/$($wf.path)" -H "Content-Type: application/json" -d $wf.data
    Write-Host ""
}
```

## Next Steps

1. ✅ Import all workflows to n8n
2. ✅ Activate all workflows
3. ✅ Test each webhook individually
4. ✅ Test via Provisioning Agent API
5. ✅ Test full Orchestrator workflow
6. 🚀 Build Scheduler Agent (if needed)

## Notes

- All workflows use **mock data** for testing
- In production, replace Function nodes with real API calls
- Add authentication if deploying publicly
- Monitor n8n logs for debugging: `docker logs -f n8n-cont`

## Support

See agent-specific integration guides:
- [Provisioning Agent Integration Guide](../provisioning-agent/INTEGRATION_GUIDE.md)
- [Orchestrator Implementation Summary](../orchestrator-agent/IMPLEMENTATION_SUMMARY.md)
