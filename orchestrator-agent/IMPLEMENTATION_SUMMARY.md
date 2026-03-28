# Orchestrator Agent - Implementation Summary

## ✅ What Has Been Created

### 📁 Project Structure
```
orchestrator-agent/
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── orchestrator.py          # Core agent logic with Gemini
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                    # PostgreSQL connection
│   ├── messaging/
│   │   ├── __init__.py
│   │   └── redis_client.py          # Redis Streams for MCP
│   ├── models/
│   │   ├── __init__.py
│   │   └── workflow_model.py        # SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── mcp_message.py           # MCP message schemas
│   │   └── workflow.py              # Workflow schemas
│   ├── __init__.py
│   └── main.py                      # FastAPI application
├── .env.example                     # Environment template
├── .gitignore
├── CREDENTIALS_GUIDE.md             # How to get API keys
├── docker-compose.yml               # Docker orchestration
├── Dockerfile
├── README.md                        # Documentation
├── requirements.txt                 # Python dependencies
├── setup.ps1                        # Automated setup script
└── test_orchestrator.py             # Test suite
```

### 🎯 Core Features Implemented

1. **Gemini-Powered Workflow Planning**
   - Task decomposition using Gemini 2.0 Flash
   - Intelligent delegation logic
   - Structured JSON output

2. **MCP-Style Communication**
   - Redis Streams for message passing
   - Structured message envelopes
   - Agent-to-agent communication

3. **Workflow State Management**
   - PostgreSQL for persistent storage
   - State transitions tracking
   - Task retry logic

4. **RESTful API**
   - FastAPI endpoints
   - Async support
   - OpenAPI documentation

5. **Docker Support**
   - Multi-container setup
   - Redis + PostgreSQL included
   - Production-ready configuration

---

## 🚀 Quick Start Instructions

### Step 1: Navigate to Directory
```powershell
cd C:\AgenticHR\orchestrator-agent
```

### Step 2: Run Setup Script
```powershell
.\setup.ps1
```
This will:
- Create virtual environment
- Install dependencies
- Create `.env` file
- Create logs directory
- Check Redis/PostgreSQL

### Step 3: Get Gemini API Key

**IMPORTANT:** You need a Google Gemini API key.

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Get API Key"
4. Copy the key (looks like: `AIzaSy...`)

### Step 4: Configure .env File

Open `.env` and update:
```env
# Required: Add your Gemini API key
GOOGLE_API_KEY=your-google-api-key-here

# Required: Set PostgreSQL password
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/agentichr
```

### Step 5: Start Required Services

#### Option A: Using Docker (Recommended)
```powershell
# Start Redis and PostgreSQL
docker-compose up -d redis postgres

# Verify they're running
docker-compose ps
```

#### Option B: Install Locally
```powershell
# Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# PostgreSQL (Download from postgresql.org)
# Then create database:
psql -U postgres -c "CREATE DATABASE agentichr;"
```

### Step 6: Start Orchestrator Agent
```powershell
# Activate virtual environment (if not already)
.\venv\Scripts\Activate.ps1

# Run the service
python -m uvicorn src.main:app --reload --port 8001
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 7: Test the Agent
```powershell
# In a new terminal
python test_orchestrator.py
```

Or test manually:
```powershell
# Check health
curl http://localhost:8001/health

# Initiate onboarding
curl -X POST http://localhost:8001/onboarding/initiate `
  -H "Content-Type: application/json" `
  -d '{
    "tenant_id": "acme_corp",
    "employee_id": "EMP001",
    "employee_name": "Alice Johnson",
    "employee_email": "alice@acme.com",
    "role": "Software Engineer",
    "department": "Engineering",
    "start_date": "2026-03-01",
    "manager_email": "manager@acme.com"
  }'
```

---

## 📋 What the Orchestrator Does

### Workflow: Onboarding Initiation

1. **Receives Request** from HR Admin
   ```json
   POST /onboarding/initiate
   {
     "tenant_id": "acme_corp",
     "employee_id": "EMP001",
     "employee_name": "Alice",
     ...
   }
   ```

2. **Creates Workflow** in PostgreSQL
   - Generates unique `workflow_id`
   - Sets status to `CREATED`
   - Stores employee data

3. **Plans Tasks** using Gemini 2.0
   - Analyzes onboarding requirements
   - Breaks into atomic tasks:
     - `create_hr_record` → Provisioning Agent
     - `create_it_ticket` → Provisioning Agent
     - `schedule_induction` → Scheduler Agent
     - `initiate_conversation` → Liaison Agent

4. **Delegates Tasks** via Redis Streams
   - Creates MCP message for each task
   - Publishes to agent-specific streams
   - Updates workflow state to `INITIATED`

5. **Tracks Progress**
   - Receives task results from agents
   - Updates task status
   - Handles retries (up to 2 attempts)
   - Marks workflow `COMPLETED` or `FAILED`

### State Machine
```
CREATED
  ↓
INITIATED (tasks delegated)
  ↓
PROVISIONING_PENDING (waiting for HRIS/IT)
  ↓
SCHEDULING_PENDING (waiting for meetings)
  ↓
WAITING_APPROVAL (if approval needed)
  ↓
ACTIVE (employee interacting)
  ↓
COMPLETED ✓ / FAILED ✗
```

---

## 🔧 Configuration Details

### Gemini Model
- **Model**: `gemini-2.0-flash-exp`
- **Purpose**: Task decomposition, workflow planning
- **Free Tier**: 15 RPM, 1500 RPD
- **Cost** (if exceeded): $0.10/1M input tokens, $0.40/1M output tokens

### Redis Streams
- **Purpose**: Inter-agent message passing
- **Streams**:
  - `agent_stream:orchestrator_agent`
  - `agent_stream:liaison_agent`
  - `agent_stream:provisioning_agent`
  - `agent_stream:scheduler_agent`
  - `agent_stream:guide_agent`

### PostgreSQL Tables
- **workflows**: Workflow metadata and state
  - `workflow_id` (PK)
  - `tenant_id`, `employee_id`
  - `status`, `created_at`, `completed_at`
  
- **tasks**: Individual task tracking
  - `task_id` (PK)
  - `workflow_id` (FK)
  - `task_type`, `assigned_agent`
  - `status`, `result`, `error`
  - `retry_count`, `max_retries`

---

## 🌐 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/onboarding/initiate` | POST | Start onboarding workflow |
| `/tasks/result` | POST | Receive task results from agents |
| `/workflows/{id}` | GET | Get workflow details |
| `/workflows` | GET | List workflows (filtered by tenant) |

### Example: Get Workflow
```powershell
curl http://localhost:8001/workflows/WF_acme_corp_EMP001_abc123
```

Response:
```json
{
  "workflow_id": "WF_acme_corp_EMP001_abc123",
  "tenant_id": "acme_corp",
  "employee_name": "Alice Johnson",
  "status": "INITIATED",
  "tasks": [
    {
      "task_id": "TASK_xyz789",
      "task_type": "create_hr_record",
      "assigned_agent": "provisioning_agent",
      "status": "PENDING",
      "retry_count": 0
    }
  ]
}
```

---

## 🔗 Integration Points

### With Other Agents
The Orchestrator delegates to:

1. **Liaison Agent** (Port 8002)
   - Initiates conversation with new hire
   - Handles policy queries routing

2. **Guide Agent** (Port 8000) - ✅ Already Implemented
   - Called by Liaison for RAG queries
   - No direct communication from Orchestrator

3. **Provisioning Agent** (Port 8003) - To Be Built
   - Creates HRIS records
   - Opens IT tickets

4. **Scheduler Agent** (Port 8004) - To Be Built
   - Schedules meetings
   - Sends calendar invites

### With External Systems (via n8n)
- Approval workflows
- Email notifications
- Calendar integrations
- HRIS API calls
- IT ticketing systems

---

## 📊 Monitoring & Debugging

### View Logs
```powershell
Get-Content logs/orchestrator.log -Wait -Tail 50
```

### Check Redis Streams
```powershell
# Connect to Redis
docker exec -it agentichr-redis redis-cli

# List streams
KEYS agent_stream:*

# Check stream length
XLEN agent_stream:orchestrator_agent

# Read messages
XREAD COUNT 10 STREAMS agent_stream:provisioning_agent 0
```

### Check Database
```powershell
# Connect to PostgreSQL
docker exec -it agentichr-postgres psql -U postgres -d agentichr

# View workflows
SELECT workflow_id, employee_name, status, created_at FROM workflows;

# View tasks
SELECT task_id, task_type, assigned_agent, status FROM tasks;
```

---

## 🐛 Troubleshooting

### "Connection refused" on port 8001
- Check if service is running
- Verify port not in use: `netstat -ano | findstr :8001`

### "Invalid API key"
- Verify `GOOGLE_API_KEY` in `.env`
- Check key at: https://aistudio.google.com/app/apikey
- Ensure no extra spaces or quotes

### "Database connection failed"
- Verify PostgreSQL is running
- Check `DATABASE_URL` format
- Test connection: `psql -U postgres -d agentichr`

### "Redis connection refused"
- Verify Redis is running: `docker ps | findstr redis`
- Check port 6379 is available

### Gemini API rate limit
- Free tier: 15 requests/minute
- Wait 60 seconds between tests
- Check quota: https://aistudio.google.com/

---

## 🎯 Next Steps

### Immediate
1. ✅ Get Gemini API key
2. ✅ Configure `.env`
3. ✅ Start Redis & PostgreSQL
4. ✅ Run Orchestrator Agent
5. ✅ Test with `test_orchestrator.py`

### Coming Next
1. **Liaison Agent** - Conversational interface
2. **Provisioning Agent** - IT/HRIS integration
3. **Scheduler Agent** - Calendar management
4. **Frontend** - Next.js UI for HR Admin
5. **n8n Workflows** - External system integration

### For Production
1. Set up proper authentication
2. Enable HTTPS/TLS
3. Configure monitoring (Prometheus/Grafana)
4. Set up log aggregation (ELK stack)
5. Implement rate limiting
6. Add API key rotation
7. Set up backup strategy

---

## 📚 Additional Resources

- **Gemini API**: https://ai.google.dev/docs
- **Redis Streams**: https://redis.io/docs/data-types/streams/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Docker Compose**: https://docs.docker.com/compose/

---

## 💡 Architecture Notes

### Why Gemini 2.0 Flash?
- Fast response times (< 500ms)
- Cost-effective for frequent calls
- Free during preview period
- Structured output support
- 1M token context window

### Why Redis Streams?
- Purpose-built for message passing
- Consumer groups for reliability
- Persistence without heavy overhead
- Simple to scale horizontally
- Native acknowledgment support

### Why PostgreSQL?
- ACID compliance for workflows
- Rich query capabilities
- JSON support for flexible data
- Battle-tested reliability
- Easy to backup and replicate

---

## 🎓 For Your Project Presentation

### Key Highlights:
1. **True Multi-Agent System** - Not just a chatbot
2. **Structured Communication** - MCP-style message passing
3. **AI-Powered Planning** - Gemini for task decomposition
4. **Production-Grade** - Docker, databases, proper architecture
5. **Scalable Design** - Microservices, message queues
6. **Multi-Tenant** - Supports multiple companies
7. **Fault Tolerant** - Retry logic, error handling

### Demo Flow:
1. Show architecture diagram
2. Start all services (Docker Compose)
3. Initiate onboarding via API
4. Show Gemini decomposing tasks
5. Show Redis messages flowing
6. Show workflow state in database
7. Demonstrate agent communication

---

**Author**: Orchestrator Agent Implementation
**Date**: February 15, 2026
**Version**: 1.0.0

