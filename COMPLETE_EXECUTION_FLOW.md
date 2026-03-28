# Complete Execution Flow - HR to All Agents

## 🎯 Overview

This document traces the **complete execution flow** from when HR initiates an onboarding request through all agents in the AgenticHR system, including how the Liaison Agent interacts with both HR and the new employee.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgenticHR System                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  Guide   │    │Orchestr- │    │ Liaison  │    │Provision │      │
│  │  Agent   │◄───┤  ator    │◄───┤  Agent   │    │  Agent   │      │
│  │(Port 8000)│   │  Agent   │    │(Port 8002)│   │(Port 8003)│     │
│  └──────────┘    │(Port 8001)│   └──────────┘    └──────────┘      │
│       ▲          └─────┬────┘          ▲               │            │
│       │                │               │               │            │
│       │                │               │               ▼            │
│  Policy Q          Workflow       Conversation    ┌─────────┐      │
│       │            Mgmt                │           │   n8n   │      │
│       │                │               │           │Workflows│      │
│       │                ▼               │           │Port 5678│      │
│       │          ┌──────────┐          │           └─────────┘      │
│       │          │ MongoDB  │          │                            │
│       │          │Port 27017│          │                            │
│       │          └──────────┘          │                            │
│       │                                │                            │
│       └────────────┬───────────────────┘                            │
│                    │                                                │
│              ┌──────────┐                                           │
│              │  Redis   │                                           │
│              │ Streams  │                                           │
│              │Port 6379 │                                           │
│              └──────────┘                                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

External Users:
┌──────────┐         ┌──────────┐
│ HR Admin │         │   New    │
│          │         │ Employee │
└──────────┘         └──────────┘
```

---

## 📋 Complete Execution Flow

### **Scenario 1: HR Initiates Onboarding (Direct API)**

#### **Step 1: HR Admin Submits Onboarding Request**

```powershell
# HR Admin executes:
curl -X POST http://localhost:8001/onboarding/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme_corp",
    "employee_id": "EMP001",
    "employee_name": "Alice Johnson",
    "employee_email": "alice.johnson@acme.com",
    "role": "Software Engineer",
    "department": "Engineering",
    "start_date": "2026-03-01",
    "manager_email": "manager@acme.com"
  }'
```

**What happens:**
- Request hits **Orchestrator Agent** at `POST /onboarding/initiate`
- File: [orchestrator-agent/src/main.py](orchestrator-agent/src/main.py#L61)

---

#### **Step 2: Orchestrator Creates Workflow**

**Code Location:** [orchestrator-agent/src/agent/orchestrator.py](orchestrator-agent/src/agent/orchestrator.py#L91)

```python
def initiate_onboarding(self, request: OnboardingInitiation) -> Workflow:
    # Generate unique workflow ID
    workflow_id = f"WF_{request.tenant_id}_{request.employee_id}_{uuid.uuid4().hex[:8]}"
    
    # Create workflow object
    workflow = Workflow(
        workflow_id=workflow_id,
        tenant_id=request.tenant_id,
        employee_id=request.employee_id,
        employee_name=request.employee_name,
        employee_email=request.employee_email,
        role=request.role,
        department=request.department,
        start_date=request.start_date,
        manager_email=request.manager_email,
        status=WorkflowStatus.CREATED
    )
    
    # Save to MongoDB
    save_workflow_to_db(workflow)
```

**Result:**
- Workflow created: `WF_acme_corp_EMP001_6b5c2d00`
- Status: `CREATED`
- Stored in MongoDB `workflows` collection

---

#### **Step 3: Orchestrator Uses Gemini AI to Plan Tasks**

**Code Location:** [orchestrator-agent/src/agent/orchestrator.py](orchestrator-agent/src/agent/orchestrator.py#L139)

**AI Prompt to Gemini:**
```
Onboarding workflow initiated:
- Workflow ID: WF_acme_corp_EMP001_6b5c2d00
- Tenant: acme_corp
- Employee: Alice Johnson (EMP001)
- Email: alice.johnson@acme.com
- Role: Software Engineer
- Department: Engineering
- Start Date: 2026-03-01

Plan the onboarding tasks and delegate them.
```

**Gemini Response (or Fallback Default Plan):**

The Orchestrator creates **4 tasks**:

1. **Create HR Record** → Provisioning Agent
2. **Create IT Ticket** → Provisioning Agent  
3. **Schedule Induction** → Scheduler Agent *(not yet built)*
4. **Initiate Conversation** → Liaison Agent

**Code Location:** [orchestrator-agent/src/agent/orchestrator.py](orchestrator-agent/src/agent/orchestrator.py#L204)

---

#### **Step 4: Orchestrator Delegates Tasks via Redis**

For each task, Orchestrator:

1. Creates task record in MongoDB
2. Publishes MCP message to Redis Streams

**Example Task 1: Create HR Record**

```python
# Task creation
task = {
    "task_id": "TASK_a1b2c3d4",
    "task_type": "create_hr_record",
    "assigned_agent": "provisioning_agent",
    "payload": {
        "employee_id": "EMP001",
        "employee_name": "Alice Johnson",
        "employee_email": "alice.johnson@acme.com",
        "role": "Software Engineer",
        "department": "Engineering"
    },
    "priority": 5,
    "retry_count": 0
}

# Publish to Redis
redis_client.publish_to_stream(
    stream_key="provisioning_agent_tasks",
    message=task
)
```

**Redis Streams Used:**
- `provisioning_agent_tasks` - For Provisioning Agent
- `scheduler_agent_tasks` - For Scheduler Agent  
- `liaison_agent_tasks` - For Liaison Agent

---

#### **Step 5: Provisioning Agent Receives Tasks**

**Code Location:** [provisioning-agent/src/agent/provisioning.py](provisioning-agent/src/agent/provisioning.py#L78)

**Background Listener:**
```python
async def listen_for_tasks():
    """Listen for tasks from Redis Streams."""
    while True:
        # Read from Redis stream with timeout
        messages = await redis_client.read_stream(
            stream_key="provisioning_agent_tasks",
            consumer_group="provisioning_consumers",
            block=1000  # 1 second timeout
        )
        
        for message in messages:
            # Process each task
            await process_task(message)
```

**Task Processing Flow:**

1. **Validate Payload** - Check required fields
2. **Check Idempotency** - Prevent duplicate execution
3. **Route to Handler** - Based on `task_type`
4. **Call n8n Webhook** - Execute external system integration
5. **Return Result** - Update workflow status

---

#### **Step 6: Provisioning Agent Calls n8n Webhooks**

**Code Location:** [provisioning-agent/src/webhooks/n8n_client.py](provisioning-agent/src/webhooks/n8n_client.py#L96)

**Task 1: Create HR Record**
```python
# Provisioning Agent calls n8n
response = await n8n_client.create_hr_record(
    tenant_id="acme_corp",
    employee_data={
        "employee_id": "EMP001",
        "employee_name": "Alice Johnson",
        "employee_email": "alice.johnson@acme.com",
        "role": "Software Engineer"
    }
)

# n8n webhook URL: http://localhost:5678/webhook/create-hr-record
```

**n8n Workflow Execution:**
- Receives HTTP POST
- Generates unique record ID: `HR_1771907199998_rp6ojuez0`
- Logs to console
- Returns success response

**Task 2: Create IT Ticket**
```python
response = await n8n_client.create_it_ticket(
    tenant_id="acme_corp",
    ticket_data={
        "employee_id": "EMP001",
        "required_systems": ["email", "vpn", "collaboration_tools"]
    }
)

# n8n webhook URL: http://localhost:5678/webhook/create-it-ticket
```

**n8n Response:**
```json
{
  "status": "success",
  "data": {
    "ticket_id": "IT_1771907200714_wvug0e8v1",
    "priority": "HIGH",
    "estimated_completion": "2026-02-25T04:46:09.668Z"
  }
}
```

---

### **Scenario 2: New Employee Messages via Liaison Agent**

#### **Step 1: New Employee Sends Message**

**Employee Action:**
```
Alice Johnson opens the onboarding portal and types:
"What is the company's work-from-home policy?"
```

**API Call:**
```powershell
curl -X POST http://localhost:8002/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice.johnson",
    "user_name": "Alice Johnson",
    "tenant_id": "acme_corp",
    "workflow_id": "WF_acme_corp_EMP001_6b5c2d00",
    "message": "What is the company work-from-home policy?",
    "metadata": {}
  }'
```

**What happens:**
- Request hits **Liaison Agent** at `POST /message`
- File: [liaison-agent/src/api/main.py](liaison-agent/src/api/main.py#L76)

---

#### **Step 2: Liaison Agent Classifies Intent**

**Code Location:** [liaison-agent/src/agent/liaison.py](liaison-agent/src/agent/liaison.py#L212)

**AI Processing:**
```python
# Liaison Agent uses Gemini to classify intent
response = self.model.generate_content([
    self.system_prompt,
    f"USER MESSAGE: {user_message}",
    "Provide ONLY JSON response"
])

# Gemini classifies this as POLICY_QUERY
```

**Intent Classification Result:**
```json
{
  "action": "route_to_guide",
  "intent_type": "POLICY_QUERY",
  "confidence_score": 0.95,
  "payload": {
    "original_message": "What is the company work-from-home policy?",
    "search_keywords": ["work from home", "policy", "remote work"],
    "expected_answer_type": "policy_explanation"
  },
  "reason": "User is asking about company policy - route to Guide Agent for RAG-based answer"
}
```

---

#### **Step 3: Liaison Routes to Guide Agent**

**Code Location:** [liaison-agent/src/api/main.py](liaison-agent/src/api/main.py#L307)

**Background Task:**
```python
async def _route_to_guide(routing_result: dict, user_id: str):
    # Create MCP message
    mcp_message = {
        "message_id": "msg_uuid",
        "from_agent": "liaison_agent",
        "to_agent": "guide_agent",
        "message_type": "QUERY",
        "workflow_id": "WF_acme_corp_EMP001_6b5c2d00",
        "tenant_id": "acme_corp",
        "payload": routing_result["payload"],
        "timestamp": "2026-02-28T10:30:00Z"
    }
    
    # Publish to Redis
    redis_client.publish_message(mcp_message)
```

**Redis Stream:** `guide_agent_queries`

**Immediate Response to User:**
```json
{
  "response_text": "Let me check the policy information for you...",
  "intent_type": "POLICY_QUERY",
  "confidence_score": 0.95,
  "action_taken": "route_to_guide"
}
```

---

#### **Step 4: Guide Agent Searches Knowledge Base**

**Guide Agent** (from agentic-rag folder):
- Listens on Redis stream `guide_agent_queries`
- Receives policy query
- Uses **RAG (Retrieval Augmented Generation)** with Qdrant vector DB
- Searches company policy documents
- Generates contextual answer using Gemini

**RAG Process:**
1. **Embed Query** - Convert question to vector
2. **Search Qdrant** - Find similar policy chunks
3. **Retrieve Context** - Get top 5 relevant passages
4. **Generate Answer** - Use Gemini with retrieved context

**Guide Response:**
```json
{
  "answer": "According to the company's Work-from-Home Policy (updated Q1 2026), employees can work remotely up to 3 days per week after completing their probation period. Remote work requires manager approval and must be scheduled in advance. Equipment for home office setup is provided by IT department.",
  "sources": [
    "HR_Policy_WFH_2026.pdf - Page 3",
    "Employee_Handbook_v4.2.pdf - Section 5.3"
  ],
  "confidence": 0.92
}
```

---

#### **Step 5: Guide Sends Response Back to Liaison**

**MCP Message:**
```python
# Guide Agent publishes response
redis_client.publish_message({
    "message_id": "resp_uuid",
    "from_agent": "guide_agent",
    "to_agent": "liaison_agent",
    "message_type": "QUERY_RESPONSE",
    "workflow_id": "WF_acme_corp_EMP001_6b5c2d00",
    "payload": {
        "answer": "...",
        "sources": [...],
        "confidence": 0.92
    }
})
```

---

#### **Step 6: Liaison Formats and Delivers to User**

**Code Location:** [liaison-agent/src/agent/liaison.py](liaison-agent/src/agent/liaison.py#L280)

**Liaison processes Guide's response:**
```python
def process_guide_response(self, guide_response: str, ...):
    # Format conversational response
    result = {
        "action": "acknowledge",
        "user_response": guide_response,
        "sources": [...],
        "follow_up_suggestions": [
            "Would you like to know about the equipment request process?",
            "Do you have questions about the probation period?"
        ]
    }
    return result
```

**Final Response to Alice:**
```
According to the company's Work-from-Home Policy, employees can work remotely up to 3 days per week after completing their probation period...

Sources:
• HR_Policy_WFH_2026.pdf - Page 3
• Employee_Handbook_v4.2.pdf - Section 5.3

Would you like to know more about remote work equipment?
```

---

### **Scenario 3: Employee Requests Action via Liaison**

#### **Step 1: Employee Requests Laptop**

**Employee Message:**
```
"I need to request a MacBook Pro for my work"
```

**API Call:**
```powershell
curl -X POST http://localhost:8002/message \
  -d '{
    "user_id": "alice.johnson",
    "message": "I need to request a MacBook Pro for my work",
    "tenant_id": "acme_corp"
  }'
```

---

#### **Step 2: Liaison Classifies as Task Request**

**Gemini Classification:**
```json
{
  "action": "delegate_to_orchestrator",
  "intent_type": "TASK_REQUEST",
  "confidence_score": 0.88,
  "payload": {
    "original_message": "I need to request a MacBook Pro for my work",
    "structured_data": {
      "task_type": "request_laptop",
      "laptop_spec": "MacBook Pro",
      "employee_id": "EMP001"
    }
  },
  "reason": "User is requesting tangible action - delegate to Orchestrator"
}
```

---

#### **Step 3: Liaison Delegates to Orchestrator**

**Code Location:** [liaison-agent/src/api/main.py](liaison-agent/src/api/main.py#L325)

```python
async def _delegate_to_orchestrator(routing_result: dict, user_id: str):
    # Create task delegation message
    mcp_message = {
        "from_agent": "liaison_agent",
        "to_agent": "orchestrator_agent",
        "message_type": "TASK_REQUEST",
        "payload": routing_result["payload"]
    }
    
    # Publish to Redis
    redis_client.publish_message(mcp_message)
```

**User Response:**
```
"I'll process your laptop request and get back to you shortly."
```

---

#### **Step 4: Orchestrator Creates Sub-Workflow**

**Orchestrator receives task request from Liaison:**
- Creates new task in existing workflow
- Delegates to Provisioning Agent
- Tracks status

```python
# Create task
task = {
    "task_id": "TASK_xyz789",
    "task_type": "request_laptop",
    "assigned_agent": "provisioning_agent",
    "payload": {
        "employee_id": "EMP001",
        "laptop_spec": "MacBook Pro 16 M3 Max"
    }
}

# Delegate to Provisioning
redis_client.publish_to_stream("provisioning_agent_tasks", task)
```

---

#### **Step 5: Provisioning Agent Executes**

**Provisioning Agent:**
1. Receives task from Redis
2. Calls n8n webhook `/webhook/request-laptop`
3. n8n creates procurement request
4. Returns result

**n8n Response:**
```json
{
  "status": "success",
  "data": {
    "request_id": "LAPTOP_1771908882491",
    "request_status": "APPROVED",
    "estimated_delivery": "2026-03-03",
    "delivery_days": 7
  }
}
```

---

#### **Step 6: Result Flows Back to User**

**Flow:**
1. Provisioning → Orchestrator (task complete)
2. Orchestrator → Liaison (result notification)
3. Liaison → User (friendly message)

**Final Message to Alice:**
```
Great news! Your MacBook Pro request has been approved. 

Request ID: LAPTOP_1771908882491
Estimated Delivery: March 3, 2026 (7 business days)

You'll receive an email confirmation shortly.
```

---

## 🔄 Complete Message Flow Summary

### **HR → System Flow**

```
HR Admin
   │
   │ POST /onboarding/initiate
   ▼
Orchestrator Agent (Port 8001)
   │
   ├─► MongoDB (Save workflow)
   │
   ├─► Gemini AI (Plan tasks)
   │
   └─► Redis Streams (Publish tasks)
         │
         ├─► provisioning_agent_tasks
         ├─► scheduler_agent_tasks  
         └─► liaison_agent_tasks
               │
               ▼
         Provisioning Agent (Port 8003)
               │
               ├─► Check idempotency
               ├─► Validate payload
               └─► Call n8n webhook
                     │
                     ▼
                  n8n (Port 5678)
                     │
                     ├─► Create HR Record
                     ├─► Create IT Ticket
                     ├─► Assign Access
                     └─► Return results
```

---

### **Employee ↔ Liaison Flow**

```
New Employee (Alice)
   │
   │ "What is the WFH policy?"
   ▼
Liaison Agent (Port 8002)
   │
   ├─► Gemini AI (Classify intent)
   │   └─► Result: POLICY_QUERY
   │
   └─► Redis Stream: guide_agent_queries
         │
         ▼
    Guide Agent (Port 8000)
         │
         ├─► Qdrant Vector DB (Search)
         ├─► Retrieve policy docs
         └─► Gemini AI (Generate answer)
               │
               ▼
         Redis Stream: liaison_agent_responses
               │
               ▼
    Liaison Agent
               │
               │ Format response
               ▼
         New Employee (Alice)
         
         "According to company policy..."
```

---

### **Employee → Action Request Flow**

```
New Employee (Alice)
   │
   │ "I need a MacBook Pro"
   ▼
Liaison Agent
   │
   ├─► Gemini AI (Classify)
   │   └─► Result: TASK_REQUEST
   │
   └─► Redis: orchestrator_agent_tasks
         │
         ▼
    Orchestrator Agent
         │
         ├─► Create workflow task
         └─► Redis: provisioning_agent_tasks
               │
               ▼
         Provisioning Agent
               │
               └─► n8n: /webhook/request-laptop
                     │
                     ▼
                  Result: APPROVED
                     │
                     ▼
               Provisioning → Orchestrator
                     │
                     ▼
               Orchestrator → Liaison
                     │
                     ▼
               Liaison → Employee
                     │
                     ▼
         "Request approved! Delivery: March 3"
```

---

## 📊 Agent Responsibilities Matrix

| Agent | Port | Primary Role | Communicates With | Data Store |
|-------|------|-------------|------------------|------------|
| **Orchestrator** | 8001 | Workflow planning, task delegation | All agents via Redis | MongoDB |
| **Liaison** | 8002 | Intent detection, conversational routing | Guide, Orchestrator, Users | Redis (temp) |
| **Guide** | 8000 | Policy Q&A using RAG | Liaison only | Qdrant Vector DB |
| **Provisioning** | 8003 | Execute provisioning tasks | Orchestrator, n8n | Redis (task queue) |
| **Scheduler** | *TBD* | Schedule meetings/events | Orchestrator, n8n | Redis (task queue) |

---

## 🔐 Key Design Principles

### **1. No Direct Agent-to-Agent HTTP Calls**
- All communication via **Redis Streams** (MCP-style messages)
- Enables loose coupling and async processing

### **2. Liaison as Single User Interface**
- All employee/HR conversations go through Liaison
- Liaison never executes tasks directly - only routes

### **3. Orchestrator as Central Controller**
- Only Orchestrator creates/manages workflows
- All task delegation flows through Orchestrator

### **4. Specialized Agents**
- Guide: RAG-based knowledge retrieval only
- Provisioning: External system integration only  
- Scheduler: Calendar/meeting management only

### **5. Idempotency Everywhere**
- All task_ids are unique
- Duplicate detection prevents re-execution
- Safe to retry failed tasks

---

## 🚀 Running the Complete Flow

### **Start All Agents:**

```powershell
# Terminal 1: Start Redis & n8n (Docker)
docker start agentichr-redis n8n-cont

# Terminal 2: Start Orchestrator
cd orchestrator-agent
cmd /k "C:/ProgramData/Anaconda3/Scripts/activate && conda activate agenticHR && python -m uvicorn src.main:app --port 8001"

# Terminal 3: Start Liaison
cd liaison-agent  
cmd /k "C:/ProgramData/Anaconda3/Scripts/activate && conda activate agenticHR && python -m uvicorn src.api.main:app --port 8002"

# Terminal 4: Start Provisioning
cd provisioning-agent
cmd /k "C:/ProgramData/Anaconda3/Scripts/activate && conda activate agenticHR && python -m uvicorn src.main:app --port 8003"

# Terminal 5: Guide Agent (if RAG needed)
cd agentic-rag
# Follow guide agent startup instructions
```

### **Test Complete Flow:**

```powershell
# 1. HR initiates onboarding
curl -X POST http://localhost:8001/onboarding/initiate -d "@test-payloads/test-onboarding.json"

# 2. Employee asks policy question
curl -X POST http://localhost:8002/message -d '{
  "user_id": "alice",
  "tenant_id": "acme_corp",
  "message": "What is the WFH policy?"
}'

# 3. Employee requests action
curl -X POST http://localhost:8002/message -d '{
  "user_id": "alice",
  "tenant_id": "acme_corp",  
  "message": "I need a laptop"
}'
```

---

## ✅ Verification Checklist

- [ ] All 4 agents running (8000, 8001, 8002, 8003)
- [ ] Redis container running (6379)
- [ ] n8n container running (5678)
- [ ] MongoDB running (27017)
- [ ] All 8 n8n workflows published
- [ ] Test HR onboarding initiation
- [ ] Test employee policy query  
- [ ] Test employee action request
- [ ] Check MongoDB for workflow records
- [ ] Check Redis streams for messages
- [ ] Check n8n executions for success

---

**End of Flow Documentation** 🎉
