# Orchestrator Agent - Step-by-Step Checklist

## ✅ Pre-Setup Checklist

Before starting, ensure you have:
- [ ] Python 3.11+ installed
- [ ] Docker Desktop installed (for Redis/PostgreSQL)
- [ ] Google account (for Gemini API)
- [ ] Internet connection
- [ ] PowerShell (Windows)

---

## 📋 Setup Steps (Do Once)

### Step 1: Initial Setup
```powershell
cd C:\AgenticHR\orchestrator-agent
.\setup.ps1
```
**Verify:**
- [ ] Virtual environment created (`venv/` folder exists)
- [ ] Dependencies installed (no errors)
- [ ] `.env` file created

---

### Step 2: Get Gemini API Key

**Go to:** https://aistudio.google.com/app/apikey

**Steps:**
1. [ ] Sign in with Google account
2. [ ] Click "Get API Key" or "Create API Key"
3. [ ] Select/create a project
4. [ ] Copy the API key (format: `AIzaSy...`)

**Free Tier Limits:**
- 15 requests per minute
- 1,500 requests per day
- Free during Gemini 2.0 preview

---

### Step 3: Configure .env File

Open `C:\AgenticHR\orchestrator-agent\.env` in a text editor

**Required Changes:**
```env
# 1. Add your Gemini API key
GOOGLE_API_KEY=your-google-api-key-here

# 2. Set a secure PostgreSQL password
POSTGRES_PASSWORD=YourSecurePassword123

# 3. Update DATABASE_URL with same password
DATABASE_URL=postgresql://postgres:YourSecurePassword123@localhost:5432/agentichr
```

**Checklist:**
- [ ] `GOOGLE_API_KEY` updated (starts with `AIza`)
- [ ] `POSTGRES_PASSWORD` set (not default)
- [ ] `DATABASE_URL` updated with same password
- [ ] No spaces around `=` sign
- [ ] File saved

---

### Step 4: Verify Setup

Run this to check configuration:
```powershell
# Check if .env is configured
Select-String "GOOGLE_API_KEY=AIza" .env
```

**Expected:** Should show your API key line

If empty or shows `your-gemini-api-key-here`, go back to Step 3.

---

## 🚀 Running the Agent (Every Time)

### Quick Start (Recommended)
```powershell
cd C:\AgenticHR\orchestrator-agent
.\start.ps1
```

This script will:
1. [ ] Start Redis (Docker)
2. [ ] Start PostgreSQL (Docker)
3. [ ] Activate virtual environment
4. [ ] Start Orchestrator Agent

**Expected Output:**
```
Starting Redis...
✓ Redis started
Starting PostgreSQL...
✓ PostgreSQL started
✓ Virtual environment activated
Starting Orchestrator Agent
...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Verify Agent is Running:**
- [ ] Open browser: http://localhost:8001/health
- [ ] Should see: `{"status": "healthy", "service": "orchestrator-agent"}`

**Check API Docs:**
- [ ] Open: http://localhost:8001/docs
- [ ] Interactive API documentation loads

---

## 🧪 Testing

### Option 1: Run Test Suite
```powershell
# In a NEW terminal (keep agent running)
cd C:\AgenticHR\orchestrator-agent
.\venv\Scripts\Activate.ps1
python test_orchestrator.py
```

**Expected:**
- [ ] Health check passes
- [ ] Onboarding initiation succeeds
- [ ] Workflow created with ID
- [ ] Tasks delegated to agents

---

### Option 2: Manual Test

**Test Health:**
```powershell
curl http://localhost:8001/health
```
**Expected:** `{"status":"healthy"}`

**Test Onboarding:**
```powershell
curl -X POST http://localhost:8001/onboarding/initiate `
  -H "Content-Type: application/json" `
  -d '{
    "tenant_id": "test_company",
    "employee_id": "EMP001",
    "employee_name": "Test User",
    "employee_email": "test@company.com",
    "role": "Engineer",
    "department": "IT",
    "start_date": "2026-03-01"
  }'
```

**Expected Response:** (Verify these exist)
- [ ] `workflow_id` (e.g., `WF_test_company_EMP001_abc123`)
- [ ] `status`: `"CREATED"`
- [ ] `employee_name`: `"Test User"`
- [ ] `tenant_id`: `"test_company"`

**Check Workflow:**
```powershell
# Replace with your actual workflow_id from above
curl http://localhost:8001/workflows/WF_test_company_EMP001_abc123
```

**Expected:**
- [ ] Workflow details shown
- [ ] Multiple tasks listed
- [ ] Tasks assigned to different agents
- [ ] Tasks have status `"PENDING"`

---

## 📊 Monitoring

### View Logs
```powershell
Get-Content logs/orchestrator.log -Tail 50 -Wait
```

**Look for:**
- [ ] `"Orchestrator Agent initialized with Gemini model"`
- [ ] `"Database tables created successfully"`
- [ ] `"Created workflow WF_xxx"`
- [ ] `"Delegated task TASK_xxx to xxx_agent"`

---

### Check Redis
```powershell
# Connect to Redis
docker exec -it agentichr-redis redis-cli

# Inside Redis CLI:
KEYS agent_stream:*
XLEN agent_stream:provisioning_agent
```

**Expected:**
- [ ] See streams: `agent_stream:provisioning_agent`, `agent_stream:scheduler_agent`, etc.
- [ ] Stream length > 0 (messages queued)

---

### Check Database
```powershell
# Connect to PostgreSQL
docker exec -it agentichr-postgres psql -U postgres -d agentichr

# Inside psql:
\dt                                    # List tables
SELECT * FROM workflows;               # View workflows
SELECT * FROM tasks;                   # View tasks
\q                                     # Exit
```

**Expected:**
- [ ] Tables exist: `workflows`, `tasks`
- [ ] Workflow record created
- [ ] Multiple task records created

---

## 🛑 Stopping the Agent

### Option 1: Stop Agent Only
In the terminal running the agent, press:
- **Ctrl + C**

### Option 2: Stop All Services
```powershell
.\stop.ps1
```

This stops:
- [ ] Redis container
- [ ] PostgreSQL container

**Note:** Virtual environment stays activated. Close terminal to fully exit.

---

## ✅ Success Criteria

You know it's working when:
- [ ] Agent starts without errors
- [ ] Health endpoint responds
- [ ] POST to `/onboarding/initiate` returns workflow
- [ ] Workflow has `workflow_id` and tasks
- [ ] Logs show "Delegated task" messages
- [ ] Redis streams have messages
- [ ] Database has workflow and task records
- [ ] No error messages in logs

---

## ❌ Common Issues & Fixes

### Issue 1: "Invalid API key"
**Symptoms:** Error on startup or 400 error when initiating onboarding
**Fix:**
```powershell
# Check your API key in .env
Select-String "GOOGLE_API_KEY" .env

# Verify it starts with "AIza"
# Get new key: https://aistudio.google.com/app/apikey
```

---

### Issue 2: "Connection refused - Redis"
**Symptoms:** Agent won't start, Redis connection error
**Fix:**
```powershell
# Check if Redis is running
docker ps | Select-String "redis"

# If not running, start it:
docker run -d --name agentichr-redis -p 6379:6379 redis:7-alpine

# Or use start.ps1:
.\start.ps1
```

---

### Issue 3: "Database connection failed"
**Symptoms:** Agent starts but errors on first request
**Fix:**
```powershell
# Check PostgreSQL is running
docker ps | Select-String "postgres"

# If not running:
docker run -d --name agentichr-postgres `
  -e POSTGRES_DB=agentichr `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=YourPassword `
  -p 5432:5432 postgres:15-alpine

# Verify DATABASE_URL in .env matches password
```

---

### Issue 4: Port 8001 already in use
**Symptoms:** "Address already in use" error
**Fix:**
```powershell
# Find what's using port 8001
netstat -ano | Select-String ":8001"

# Kill the process (replace PID)
Stop-Process -Id <PID> -Force

# Or use a different port:
python -m uvicorn src.main:app --reload --port 8002
```

---

### Issue 5: "Module not found"
**Symptoms:** Import errors when starting
**Fix:**
```powershell
# Reinstall dependencies
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | Select-String "google-generativeai"
```

---

### Issue 6: Rate limit exceeded (429)
**Symptoms:** "Resource exhausted" error from Gemini
**Fix:**
- Free tier: 15 requests/minute, 1500/day
- Wait 60 seconds between tests
- Check quota: https://aistudio.google.com/
- Consider paid tier if needed

---

## 📝 Quick Reference

### Essential Commands
```powershell
# Setup (once)
.\setup.ps1

# Start agent
.\start.ps1

# Stop services
.\stop.ps1

# Run tests
python test_orchestrator.py

# View logs
Get-Content logs/orchestrator.log -Tail 50 -Wait

# Check health
curl http://localhost:8001/health

# API docs
# Browser: http://localhost:8001/docs
```

---

### Directory Structure
```
orchestrator-agent/
├── .env              ← Your credentials HERE
├── setup.ps1         ← Run once for setup
├── start.ps1         ← Run to start agent
├── stop.ps1          ← Run to stop services
├── test_orchestrator.py  ← Test suite
├── requirements.txt  ← Dependencies
├── logs/             ← Log files
│   └── orchestrator.log
└── src/              ← Source code
    ├── agent/        ← Core orchestrator logic
    ├── config/       ← Configuration
    ├── database/     ← PostgreSQL
    ├── messaging/    ← Redis Streams
    ├── models/       ← Database models
    ├── schemas/      ← MCP message schemas
    └── main.py       ← FastAPI app
```

---

## 🎯 Next Steps After Success

Once your Orchestrator Agent is working:

### Immediate Next Steps:
1. [ ] Read `IMPLEMENTATION_SUMMARY.md` for full details
2. [ ] Explore API docs at http://localhost:8001/docs
3. [ ] Try different onboarding scenarios
4. [ ] Check task delegation in logs

### Building Other Agents:
1. **Liaison Agent** (Port 8002)
   - Handles conversation with new hires
   - Integrates with Orchestrator via Redis

2. **Provisioning Agent** (Port 8003)
   - Creates HRIS records
   - Opens IT tickets via n8n

3. **Scheduler Agent** (Port 8004)
   - Schedules meetings
   - Calendar integration

### Integration:
1. Set up **n8n** for external tools
2. Create **Next.js frontend** for HR Admin
3. Connect **Guide Agent** (already implemented)
4. Configure **multi-tenant** settings

---

## 📞 Need Help?

### Troubleshooting Resources:
- `IMPLEMENTATION_SUMMARY.md` - Detailed documentation
- `CREDENTIALS_GUIDE.md` - API key setup
- `README.md` - Architecture overview
- Logs: `logs/orchestrator.log`

### Check These First:
1. `.env` file configured correctly?
2. Redis and PostgreSQL running?
3. Virtual environment activated?
4. No firewall blocking ports 6379, 5432, 8001?
5. Gemini API key valid?

---

## ✨ You're All Set!

If you've completed this checklist:
- ✅ Orchestrator Agent is running
- ✅ Tests pass
- ✅ Workflows created
- ✅ Tasks delegated

**Congratulations!** 🎉

You now have a working **AI-powered workflow orchestration agent** using:
- **Gemini 2.0** for intelligent planning
- **Redis Streams** for message passing
- **PostgreSQL** for state management
- **FastAPI** for REST API
- **Docker** for infrastructure

This is the **brain** of your AgenticHR system!

---

**Ready for the next agent?** Let your instructor know, and we'll build the **Liaison Agent** next! 🚀

