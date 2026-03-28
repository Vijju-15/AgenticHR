# AgenticHR — Complete Project Blueprint

> **Purpose of this document**: Honest, complete reference for the AgenticHR project.  
> No marketing language. No bluffs. Only what is real, what is missing, and what to build next.  
> Written for a single-company deployment first.

---

## Table of Contents

1. [The Real Problem](#1-the-real-problem)
2. [The Real Onboarding Process (Ground Truth)](#2-the-real-onboarding-process-ground-truth)
3. [How This System Maps to That Process](#3-how-this-system-maps-to-that-process)
4. [The 5 Agents — What Each One Actually Does](#4-the-5-agents--what-each-one-actually-does)
5. [What Is Actually Built Today](#5-what-is-actually-built-today)
6. [What Is Missing or Fake](#6-what-is-missing-or-fake)
7. [Full Technical Architecture](#7-full-technical-architecture)
8. [Database Schemas](#8-database-schemas)
9. [UI Screens Required](#9-ui-screens-required)
10. [The Build Roadmap](#10-the-build-roadmap)
11. [Honest Assessment](#11-honest-assessment)

---

## 1. The Real Problem

HR teams at startups and mid-size companies spend 2–5 days per new hire doing completely repetitive manual work:

- Writing and sending offer letters manually
- Chasing candidates for documents over email
- Manually creating IT accounts across multiple tools
- Copy-pasting credentials into an email and hoping it does not go to spam
- Scheduling orientation manually on Google Calendar
- Answering the same 20 questions from every new joiner about leave policy, holidays, and tools

This is not a technology problem. The tools exist. The problem is **no single system connects all of these steps together** for a small or mid-size company that cannot afford Workday or SAP SuccessFactors.

**AgenticHR's purpose**: Handle the entire post-offer onboarding lifecycle autonomously. HR clicks one button per new hire. The system handles every step from offer acceptance to Day-3 orientation.

---

## 2. The Real Onboarding Process (Ground Truth)

This is the actual sequence observed from a real intern onboarding. This is the design specification.

```
Step 1 — Offer Letter Sent
  HR generates an offer letter containing:
  - Joining date
  - Compensation details (stipend / salary)
  - Role and department
  - Company rules and regulations summary
  - Acceptance deadline
  
  Candidate receives this by email.

Step 2 — Candidate Accepts the Offer
  Candidate clicks "I Accept" or replies confirming acceptance.
  HR is notified that the candidate has accepted.

Step 3 — Document Collection
  System sends an email to the candidate asking for:
  - Government-issued ID proof (Aadhaar, Passport, etc.)
  - Recent passport photo
  - Educational qualification certificates (marksheets, degree)
  - Any other required memo/form specific to the company
  
  Candidate uploads these documents.
  HR can see the uploaded documents in their dashboard.

Step 4 — Manager Assignment Notification
  System sends an email to the candidate containing:
  - Name of their assigned manager
  - Manager's email address
  - Team they are joining
  - A short introduction to what the team does

Step 5 — Company Credentials Delivery
  System sends the candidate their login credentials:
  - Company email address (e.g., name@company.com)
  - Temporary password
  - List of tools they will have access to (GitHub, Jira, Slack, etc.)
  - Instructions to change password on first login

Step 6 — Orientation Day (Day 1)
  On the joining date:
  - Candidate collects their laptop
  - Day 1 setup is done (laptop onboarded, tools installed)
  - HR/manager does an in-person or virtual intro
  - Candidate starts their onboarding journey checklist
```

This 6-step sequence is the **functional specification** for the entire system.

---

## 3. How This System Maps to That Process

| Real Step | Who does it now (manual) | Which agent handles it | Status |
|-----------|--------------------------|------------------------|--------|
| Step 1: Offer letter | HR writes and emails manually | Orchestrator plans it → Provisioning sends via email | **Not built** |
| Step 2: Acceptance | Candidate replies to email, HR checks manually | Liaison Agent catches the acceptance message + notifies Orchestrator | **Not built** |
| Step 3: Document collection | HR emails a list, candidate replies with attachments | Liaison sends a structured upload link; HR dashboard shows uploads | **Not built** |
| Step 4: Manager notification | HR emails manually | Orchestrator task → Provisioning sends via email | **Partially built** (manager_email field exists, no email dispatch) |
| Step 5: Credentials delivery | HR creates accounts manually then emails | Provisioning Agent: `send_welcome_credentials` task | **Skeleton built, sends mock data** |
| Step 6: Day 1 setup | HR arranges everything manually | Scheduler creates calendar event; Guide gives checklist | **Scheduler built for calendar; checklist partially built** |

**Post-joining (what the system does handle well):**

| Feature | Agent | Status |
|---------|-------|--------|
| Intern asks "how many leaves do I get?" | Guide Agent (RAG) | **REAL and working** |
| Intern views their onboarding checklist | Guide + Orchestrator | **REAL (Day 1/2/3 checklist exists)** |
| Intern submits a leave request | Guide Agent tools | **REAL (leave_management tools exist)** |
| HR approves/rejects leave | HR Dashboard + Orchestrator | **REAL** |
| Orientation meeting scheduled | Scheduler Agent → Google Calendar | **REAL** |
| HR triggers onboarding from UI | Frontend → Orchestrator | **REAL** |

---

## 4. The 5 Agents — What Each One Actually Does

### Agent 1: Guide Agent (Port 8000)
**Technology**: LangGraph + LangChain + Gemini + Qdrant (vector store) + Anthropic Claude  
**File**: `agentic-rag/src/agents/multi_tenant_agentic_rag.py`

**What it actually does:**
- Accepts a `query` + `company_id` and returns an answer
- Embeds the query, retrieves matching chunks from Qdrant (the company's uploaded documents)
- Has tools for: `check_leave_balance`, `apply_leave`, `get_holiday_calendar`, `submit_leave_request`, `get_onboarding_progress`, `complete_onboarding_step`
- Supports multi-tenant: each company has an isolated Qdrant collection
- Accepts document uploads (PDF, DOCX, TXT, MD) via `POST /documents/upload`

**What it does NOT do:**
- Does not send emails
- Does not create accounts
- Does not make workflow decisions

**Honest limitation**: If no documents are uploaded for the company, the Guide Agent has no knowledge base and will return empty answers. It does not come pre-loaded with any knowledge.

---

### Agent 2: Liaison Agent (Port 8002)
**Technology**: Gemini 2.5 + FastAPI + Redis  
**File**: `liaison-agent/src/agent/liaison.py`

**What it actually does:**
- Receives a natural language message from the UI
- Classifies the intent into one of 7 types: `POLICY_QUERY`, `TASK_REQUEST`, `APPROVAL_RESPONSE`, `GENERAL_QUERY`, `LEAVE_REQUEST`, `ONBOARDING_PROGRESS`, `HR_ACTION`
- Routes `POLICY_QUERY` → Guide Agent
- Routes `TASK_REQUEST` → Orchestrator Agent
- Routes `LEAVE_REQUEST` → Orchestrator Agent
- Maintains multi-turn conversation history (stored in Redis per tenant+workflow)
- Extracts structured fields from natural language (e.g., "onboard Alice as a Data Analyst starting March 10" → extracts name, role, start_date)

**What it does NOT do:**
- Does not execute any action itself
- Does not directly call Provisioning or Scheduler
- Does not handle document uploads

**Honest limitation**: Intent classification fails on ambiguous or very short messages. The Gemini API call adds 1–3 seconds of latency per message.

---

### Agent 3: Orchestrator Agent (Port 8001)
**Technology**: Gemini 2.5 + FastAPI + MongoDB + Redis Streams  
**File**: `orchestrator-agent/src/agent/orchestrator.py`

**What it actually does:**
- Receives an onboarding initiation request (employee name, email, role, department, start date, manager email)
- Creates a workflow record in MongoDB with a unique `workflow_id`
- Uses Gemini to break the workflow into an ordered list of tasks
- Publishes each task to the appropriate Redis Stream (`agent_stream:provisioning_agent`, `agent_stream:scheduler_agent`)
- Tracks workflow state: `CREATED → INITIATED → PROVISIONING_PENDING → SCHEDULING_PENDING → ACTIVE → COMPLETED`
- Stores every task result returned by other agents
- Exposes a REST API for the frontend to query workflow status

**Current task types it delegates:**

To Provisioning Agent:
- `create_employee_record` — store employee in DB
- `generate_employee_id` — create formatted ID (DEPT-YYYY-XXXX)
- `assign_department` — assign department and manager
- `send_welcome_credentials` — send login credential email
- `initialize_onboarding` — create onboarding journey record
- `create_onboarding_checklist` — build Day 1/2/3 checklist

To Scheduler Agent:
- `schedule_meeting` — create Google Calendar event with Meet link

**Honest limitation**: The Gemini prompt decides which tasks to create. If the prompt is poorly written or Gemini gives unexpected output, the task list may be incomplete or in the wrong order. There is no hardcoded sequence — this is both the strength and the weakness of using an LLM as the planner.

---

### Agent 4: Provisioning Agent (Port 8003)
**Technology**: FastAPI + Redis + httpx (no AI/LLM)  
**File**: `provisioning-agent/src/agent/provisioning.py`

**What it actually does:**
- Listens to `agent_stream:provisioning_agent` Redis stream
- Receives structured tasks from Orchestrator
- Validates the task payload (checks required fields)
- Checks idempotency cache (will not execute the same task_id twice)
- Calls an n8n webhook for the actual execution
- Returns a structured result back to Orchestrator via Redis

**Current task handlers and what each n8n webhook does:**

| Task | n8n Webhook | What the n8n workflow actually does TODAY |
|------|-------------|-------------------------------------------|
| `create_employee_record` | `/webhook/create-hr-record` | Returns a fake HR record ID. Does nothing real. |
| `generate_employee_id` | `/webhook/generate-employee-id` | Returns a fake formatted ID. Does nothing real. |
| `assign_department` | `/webhook/assign-access` | Returns fake access confirmation. Does nothing real. |
| `send_welcome_credentials` | `/webhook/create-email` | Returns fake email confirmation. Does NOT send any email. |
| `initialize_onboarding` | None (handled internally) | Writes to MongoDB. This one IS real. |
| `create_onboarding_checklist` | None (handled internally) | Writes to MongoDB. This one IS real. |

**Honest limitation**: Every n8n webhook is a simple JavaScript Function Node that generates a fake ID and returns `status: success`. No real integration exists. The provisioning pipeline looks complete from the outside but does nothing that affects the real world.

---

### Agent 5: Scheduler Agent (Port 8004)
**Technology**: FastAPI + Redis + httpx (no AI/LLM)  
**File**: `scheduler-agent/src/agent/`

**What it actually does:**
- Listens to `agent_stream:scheduler_agent` Redis stream
- Receives scheduling tasks from Orchestrator
- Calls the n8n webhook `/webhook/schedule-meeting` (or `/webhook/schedule-induction`)
- n8n workflow uses the Google Calendar node to create a real Google Calendar event with a Google Meet link
- Returns event_id, meeting link, start/end time back to Orchestrator

**This is the most complete agent in the system.** When Google credentials are configured in n8n, it creates real calendar invites with real Meet links and sends invite emails to attendees.

**Honest limitation**: Requires Google Cloud OAuth credentials to be set up in n8n. Without that configuration, the n8n Google Calendar node will fail and return an error.

---

## 5. What Is Actually Built Today

Here is a precise inventory of what works end-to-end:

### ✅ Real and Working (given API keys are set)
- **Guide Agent RAG pipeline**: Upload a PDF → ask questions → get answers grounded in the document
- **Leave management**: Intern submits leave request → Guide Agent processes it → stored in DB → HR approves/rejects from dashboard
- **Liaison intent classification**: Detects what the user wants from natural language
- **Orchestrator workflow creation**: Creates a workflow record in MongoDB with proper task breakdown
- **Redis messaging**: Agents communicate through Redis Streams reliably
- **Onboarding checklist (Day 1/2/3)**: Creates a structured checklist in MongoDB, visible on Intern Dashboard
- **Scheduler Agent → Google Calendar**: Creates real meetings (if Google OAuth configured in n8n)
- **Frontend HR Dashboard**: Shows workflows, leave approvals, email inbox (seeded), onboarding trigger form
- **Frontend Intern Dashboard**: Shows onboarding checklist progress, leave request form, chat with Guide Agent
- **Authentication**: Login/register with JWT tokens, role-based access (HR vs Employee)

### ⚠️ Partially Working
- **Welcome credentials email**: Task runs, returns "success", but no actual email is sent
- **HRIS record creation**: Task runs, returns a fake HR record ID, but no real HRIS is updated
- **Employee ID generation**: Generates and returns an ID correctly, but only in the response JSON — not persisted to any real directory or HRIS
- **Offer letter**: No concept of this exists in the system yet

### ❌ Not Built
- **Offer letter generation and delivery**
- **Offer acceptance flow** (candidate clicks "Accept")
- **Document collection** (candidate uploads ID proof, photo, certificates)
- **Document storage and HR review**
- **Manager introduction email** (automated, not just storing manager_email)
- **Real SMTP email sending** (all email tasks are fake)
- **Real HRIS integration** (all HRIS tasks are fake)

---

## 6. What Is Missing or Fake

### The Fake Part (n8n Function Nodes)
Every n8n webhook that the Provisioning Agent calls today is a JavaScript Function Node that looks like this:

```javascript
// This is what ALL the provisioning n8n workflows actually do:
return [{
  json: {
    status: "success",
    message: "HR record created successfully",
    data: {
      record_id: "HR_" + Date.now() + "_" + Math.random().toString(36).slice(2),
      system: "HRIS"
    }
  }
}]
```

That is the entire workflow. It generates a random string and returns it. There is no database write, no API call, no email sent.

### The Missing Stages

**Stage 1: Pre-onboarding (before joining date)**

The system has no concept of the gap between "HR initiates onboarding" and "the intern's first day." In reality, everything from Steps 1–5 in Section 2 happens in that gap. The current system jumps straight to Day 1 setup.

The missing workflow stages are:
```
OFFER_SENT → OFFER_ACCEPTED → DOCUMENTS_REQUESTED → DOCUMENTS_SUBMITTED 
→ MANAGER_ASSIGNED → CREDENTIALS_SENT → READY_FOR_DAY_1
```

These need to be added to the `WorkflowState` enum in the Orchestrator.

**Stage 2: Real email delivery**
No email is sent anywhere in the system today. The `send_welcome_credentials` task calls a fake n8n webhook. To fix this, the n8n workflow needs to be replaced with either:
- Gmail node (uses Google OAuth, free, real email)
- SendGrid node (uses SendGrid API key, free tier available)
- SMTP node (works with any email provider)

**Stage 3: Document upload by the candidate**
There is currently no way for an intern to upload their ID proof or certificates. The Intern Dashboard has no file upload feature. This needs:
- A file upload endpoint in the Orchestrator or a new Documents service
- File storage (local filesystem, AWS S3, or Google Drive)
- HR Dashboard view showing uploaded documents per employee

---

## 7. Full Technical Architecture

### Services and Ports
```
┌─────────────────────────────────────────────────────────┐
│                     AgenticHR System                     │
│                                                          │
│  Frontend (Next.js)          :3000                      │
│  Guide Agent (FastAPI)       :8000  ← Qdrant :6333      │
│  Orchestrator (FastAPI)      :8001  ← MongoDB :27017    │
│  Liaison Agent (FastAPI)     :8002  ← Redis  :6379      │
│  Provisioning Agent (FastAPI):8003  ↑                   │
│  Scheduler Agent (FastAPI)   :8004  ↑                   │
│  n8n (Automation)            :5678                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Communication Flow
```
User (HR) types in chat or fills onboarding form
    ↓
Frontend (Next.js :3000)
    ↓ POST /api/liaison/message
Liaison Agent (:8002)
    ↓ Intent = TASK_REQUEST
    ↓ POST http://orchestrator:8001/onboarding/initiate
Orchestrator Agent (:8001)
    ↓ Creates workflow in MongoDB
    ↓ Gemini plans tasks
    ↓ Publishes to Redis Stream: agent_stream:provisioning_agent
Provisioning Agent (:8003)
    ↓ Validates task
    ↓ POST http://n8n:5678/webhook/{task_type}
n8n Workflow
    ↓ (Today: fake. Target: Gmail / Google Sheets / real API)
    ↓ Returns result
Provisioning Agent
    ↓ Publishes result to Redis Stream: agent_stream:orchestrator_agent
Orchestrator Agent
    ↓ Updates workflow state in MongoDB
    ↓ If scheduling needed: publishes to agent_stream:scheduler_agent
Scheduler Agent (:8004)
    ↓ POST http://n8n:5678/webhook/schedule-meeting
n8n Google Calendar Workflow
    ↓ Creates Google Calendar event + Meet link (REAL)
    ↓ Returns event_id + hangoutLink
Scheduler Agent
    ↓ Publishes result
Orchestrator Agent
    ↓ Marks workflow COMPLETED in MongoDB
Frontend (polling /workflows endpoint)
    ↓ Updates workflow status in HR Dashboard
```

### Redis Streams (inter-agent message bus)
```
agent_stream:provisioning_agent  — orchestrator → provisioning
agent_stream:scheduler_agent     — orchestrator → scheduler
agent_stream:orchestrator_agent  — provisioning/scheduler → orchestrator
agent_stream:liaison_agent       — (reserved, not heavily used currently)
```

### Technology Stack (actual, not aspirational)
| Layer | Technology | Version | Used for |
|-------|-----------|---------|----------|
| LLM | Google Gemini 2.5 Flash | API | Liaison (intent), Orchestrator (planning) |
| LLM | Anthropic Claude 3.5 Sonnet | API | Guide Agent (RAG answers) |
| Vector DB | Qdrant | 1.x | Document chunk storage for Guide Agent |
| App DB | MongoDB | 7.x | Workflow state, tasks, users, leave requests |
| Message Bus | Redis Streams | 7.x | Inter-agent async communication |
| Automation | n8n | Latest | Webhook layer between agents and external tools |
| Backend | FastAPI + Pydantic | 0.115.x | All 5 agent APIs |
| Frontend | Next.js 14 + React 18 | 14.2.5 | HR Dashboard, Intern Dashboard, Chat |
| Styling | TailwindCSS | 3.4.x | Frontend |
| Embeddings | Sentence Transformers | n/a | Document chunking in Guide Agent |

---

## 8. Database Schemas

### MongoDB Collections (Orchestrator)

**workflows**
```json
{
  "workflow_id": "WF_acme_corp_EMP001_abc123",
  "tenant_id": "acme_corp",
  "employee_id": "EMP001",
  "employee_name": "Alice Johnson",
  "employee_email": "alice.johnson@acme.com",
  "role": "Software Engineer",
  "department": "Engineering",
  "start_date": "2026-03-10",
  "manager_id": null,
  "manager_email": "manager@acme.com",
  "status": "COMPLETED",
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:05:00Z",
  "completed_at": "2026-03-07T10:05:00Z",
  "metadata": {}
}
```

**workflow_tasks**
```json
{
  "task_id": "TASK_abc123",
  "workflow_id": "WF_acme_corp_EMP001_abc123",
  "tenant_id": "acme_corp",
  "task_type": "create_employee_record",
  "assigned_agent": "provisioning_agent",
  "payload": { "employee_name": "Alice Johnson", ... },
  "status": "COMPLETED",
  "result": { "record_id": "HR_123", "system": "HRIS" },
  "retry_count": 0,
  "max_retries": 2,
  "created_at": "2026-03-07T10:00:00Z",
  "completed_at": "2026-03-07T10:01:00Z"
}
```

**users** (auth)
```json
{
  "user_id": "usr_abc123",
  "tenant_id": "acme_corp",
  "email": "hr@acme.com",
  "hashed_password": "...",
  "full_name": "HR Manager",
  "role": "hr",
  "created_at": "2026-03-01T00:00:00Z"
}
```

**onboarding_journeys** (Day 1/2/3 checklist)
```json
{
  "employee_id": "EMP001",
  "tenant_id": "acme_corp",
  "employee_name": "Alice Johnson",
  "start_date": "2026-03-10",
  "overall_progress_pct": 33,
  "current_day": 1,
  "plan": [
    {
      "day": 1,
      "steps": [
        { "step_id": "d1_hr_intro", "title": "HR Introduction", "completed": true },
        { "step_id": "d1_policy_overview", "title": "Policy Overview", "completed": false },
        { "step_id": "d1_doc_submission", "title": "Document Submission", "completed": false }
      ]
    },
    {
      "day": 2,
      "steps": [
        { "step_id": "d2_manager_intro", "title": "Manager Introduction", "completed": false },
        { "step_id": "d2_team_welcome", "title": "Team Welcome", "completed": false },
        { "step_id": "d2_tool_access", "title": "Tool Access Setup", "completed": false }
      ]
    },
    {
      "day": 3,
      "steps": [
        { "step_id": "d3_training", "title": "Training Sessions", "completed": false },
        { "step_id": "d3_project_overview", "title": "Project Overview", "completed": false },
        { "step_id": "d3_first_assignment", "title": "First Assignment", "completed": false }
      ]
    }
  ]
}
```

**leave_requests**
```json
{
  "request_id": "LR_abc123",
  "tenant_id": "acme_corp",
  "employee_id": "EMP001",
  "leave_type": "sick",
  "start_date": "2026-03-15",
  "end_date": "2026-03-16",
  "days": 2,
  "reason": "Fever",
  "status": "pending",
  "created_at": "2026-03-07T10:00:00Z",
  "decided_at": null,
  "decided_by": null
}
```

### Schemas to ADD (for real onboarding flow)

**offer_letters** (needs to be built)
```json
{
  "offer_id": "OFFER_abc123",
  "tenant_id": "acme_corp",
  "workflow_id": "WF_acme_corp_EMP001_abc123",
  "candidate_name": "Alice Johnson",
  "candidate_email": "alice@gmail.com",
  "role": "Software Engineer",
  "department": "Engineering",
  "joining_date": "2026-03-10",
  "stipend": "25000",
  "status": "pending_acceptance",
  "acceptance_token": "tok_abc123",
  "sent_at": "2026-03-01T10:00:00Z",
  "accepted_at": null
}
```

**candidate_documents** (needs to be built)
```json
{
  "doc_id": "DOC_abc123",
  "tenant_id": "acme_corp",
  "workflow_id": "WF_acme_corp_EMP001_abc123",
  "employee_id": "EMP001",
  "doc_type": "govt_id",
  "filename": "aadhaar_alice.pdf",
  "storage_path": "uploads/acme_corp/EMP001/aadhaar_alice.pdf",
  "uploaded_at": "2026-03-05T14:00:00Z",
  "verified": false
}
```

---

## 9. UI Screens Required

### Screens That Exist Today
| Screen | URL | What it shows | Gaps |
|--------|-----|---------------|------|
| Login | `/login` | Email/password login, role selection | Works |
| HR Dashboard | `/hr-dashboard` | Workflows, leave approvals, email inbox, onboarding trigger | No offer letter, no document review section |
| Intern Dashboard | `/intern-dashboard` | Onboarding checklist, leave requests, chat | No offer acceptance, no document upload |
| Chat | `/chat` | Conversational interface with Liaison Agent | Works |
| Onboarding Form | `/onboarding` | HR fills employee details to trigger workflow | Works but skips offer stage |
| Workflows | `/workflows` | Live workflow status tracker | Works |

### Screens That Need to Be Built

**For HR:**
- `Offer Letter Builder` — HR selects a template, fills compensation and joining date, sends to candidate
- `Document Review` — List of uploaded documents per employee, HR marks each as verified

**For Candidate (pre-joining):**
- `Offer Acceptance Page` — Candidate opens link from email, reads offer, clicks Accept or Decline
- `Document Upload Page` — Candidate uploads required files (ID proof, photo, certificates) one by one

**Note**: The candidate's pre-joining pages do not require authentication. They are accessed via a unique tokenized URL sent in the email (like `https://acme.agentichr.com/offer/tok_abc123`). This is the same pattern used by DocuSign, Greenhouse, and every modern ATS.

---

## 10. The Build Roadmap

### Phase 1 — Make What Exists Real (2–3 weeks)
**Goal**: The existing agent pipeline should do real things, not return fake data.

**1.1 Replace fake n8n webhooks with Gmail + Google Sheets**

In n8n, replace the JavaScript Function nodes with real nodes:

- `create_hr_record` workflow: Add a **Google Sheets Append Row** node. Each new employee = new row in a spreadsheet. This is your HRIS for a single company.
- `send_welcome_credentials` workflow: Add a **Gmail Send Email** node. Send the actual credentials email to the candidate's email address.
- `create_it_ticket` workflow: Add a **Gmail Send Email** node to the IT team's address, or a **Jira Create Issue** node if the company uses Jira.

This takes about half a day in n8n. No code changes to any agent needed.

**1.2 Verify Scheduler Agent works end-to-end**

Confirm Google OAuth is configured in n8n for the Google Calendar node. Run one test and confirm a real Google Calendar event is created with a Meet link.

**1.3 Add document upload endpoint**

Add `POST /documents/upload` to the Orchestrator. Store files in a local `uploads/` folder for now (S3 later). Return a `doc_id`. Add `GET /documents/{employee_id}` for HR to list them.

---

### Phase 2 — Add Pre-Joining Flow (2–3 weeks)
**Goal**: The system handles everything from "HR adds a new hire" to "candidate's Day 1."

**2.1 Offer Letter**

- Add `offer_letters` collection to MongoDB
- Add Orchestrator endpoint: `POST /offer/send`
- Orchestrator creates offer letter record with a unique `acceptance_token`
- Provisioning Agent task: `send_offer_letter` → n8n Gmail workflow sends an email with a link like `https://yourapp.com/offer/{acceptance_token}`
- Add frontend page `/offer/[token]` (public, no auth) where candidate reads and accepts
- On accept: `POST /offer/{token}/accept` → Orchestrator updates workflow state to `OFFER_ACCEPTED`

**2.2 Document Collection**

- After offer acceptance, Orchestrator delegates `send_document_request` task → n8n Gmail sends candidate a link to `/documents/upload/{workflow_id}`
- Add frontend page `/documents/upload/[workflow_id]` (public, no auth) for candidate to upload files
- Files stored server-side, records stored in `candidate_documents` collection
- HR Dashboard shows document status per employee with a review section

**2.3 Manager Introduction Email**

- After documents are submitted, Orchestrator delegates `send_manager_introduction` task
- n8n Gmail workflow sends candidate:
  - Manager's name and email
  - Team description
  - What to expect on Day 1

**2.4 Credentials Email**

- Replace the fake `send_welcome_credentials` n8n workflow with a real Gmail node
- Template: company email, temporary password, tool access list, "please change password" instructions

---

### Phase 3 — Polish (1 week)
**Goal**: The system looks and feels complete for a demo or real deployment.

- Add workflow status timeline to HR Dashboard (visual step-by-step progress for each hire)
- Add email notifications to HR when a candidate accepts, submits documents, or misses a deadline
- Add a deadline tracker (e.g., if offer not accepted in 3 days, HR gets an alert)
- Upload company policy documents via HR Dashboard UI (currently only possible via API)

---

### Phase 4 — Multi-Company (after Phase 3 is complete and validated)
**Goal**: Any HR team can sign up, configure their company, and start using the system.

- Add company registration flow (`/signup` page)
- HR uploads their company documents during signup → Guide Agent gets company-specific knowledge base
- Add company-specific email templates (offer letter, credentials email, etc.)
- Add subdomain or `tenant_id` routing so each company has isolated data
- Replace Google Sheets HRIS with a proper records table in PostgreSQL

This phase should only start after the single-company version has been used successfully by at least one real company.

---

## 11. Honest Assessment

### What this project gets right

**The architecture is sound.** The separation of concerns — intent detection (Liaison), planning (Orchestrator), execution (Provisioning), scheduling (Scheduler), knowledge (Guide) — is the right way to build this. Each agent has one job. They communicate through Redis, which makes them independently deployable and restartable. The MongoDB state management in the Orchestrator means no workflow is ever lost, even if an agent crashes.

**The frontend is production-quality.** The HR Dashboard, Intern Dashboard, and Chat page are well-built with proper authentication, real-time polling, and clean UI. This is not a prototype UI — it can be shown to real users.

**The Guide Agent is genuinely useful right now.** Upload any company's HR policy PDF and interns can ask questions in plain English, submit leave requests, and track their onboarding progress. This works today with no additional work.

**The Scheduler Agent is genuinely useful when configured.** If you configure Google OAuth in n8n, orientation meetings are automatically created with Google Meet links. This is real automation.

### What this project needs to become real

The single missing piece that makes everything else consequential is **real email delivery**. Every touchpoint in the onboarding process — offer letter, document request, manager introduction, credentials — is an email. Right now none of them send anything. Once Gmail nodes replace the fake Function nodes in n8n, the entire pipeline becomes functional for real companies.

The second missing piece is the **pre-joining flow** (offer letter + document collection). Without it, the system can only help after someone has already joined. The most painful part of HR's job — the 2-week window between offer acceptance and Day 1 — is untouched.

### What this project is NOT

- It is not trying to replace Workday, SuccessFactors, or BambooHR. Those have payroll, compliance, and performance management. This system only handles the onboarding lifecycle.
- It is not an ATS (Applicant Tracking System). It starts after the hire decision is made. Resume screening, interviews, and hiring decisions are out of scope.
- It does not manage company IT infrastructure directly. It sends a ticket or email to whoever does. The actual laptop provisioning, account creation in Google Workspace or GitHub — those are still done by IT. The system just makes sure IT is notified immediately and automatically.

### Realistic completion estimate

Given what already exists:
- Phase 1 (make it real): If you spend 2–3 focused days on the n8n workflows and document upload endpoint, the system will be end-to-end functional with real emails and a real HRIS record (Google Sheets).
- Phase 2 (pre-joining flow): 2 weeks of work for offer letter + document collection pages.
- Phase 3 (polish): 3–5 days.
- Phase 4 (multi-company): 3–4 weeks. Not needed for proof of concept.

Total for a working single-company product: **3–4 weeks of focused work**, assuming you work alone.

---

*Last updated: March 7, 2026*  
*This document reflects the current state of the codebase as read and verified. It will need to be updated as gaps are filled.*
