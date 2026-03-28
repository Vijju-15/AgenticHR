# Provisioning Agent - Command Prompt Guide

Quick guide for running the Provisioning Agent using Windows Command Prompt (CMD).

## Prerequisites

✅ Python 3.9+ installed  
✅ Redis running (Docker container `agentichr-redis`)  
✅ Command Prompt (not PowerShell)

---

## Step 1: Setup (One-Time)

Open **Command Prompt** and navigate to the provisioning-agent folder:

```cmd
cd C:\AgenticHR\provisioning-agent
```

### Create Virtual Environment

```cmd
python -m venv venv
```

### Activate Virtual Environment

```cmd
venv\Scripts\activate.bat
```

You should see `(venv)` prefix in your prompt.

### Install Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### Create .env File

```cmd
copy .env.example .env
```

### Edit .env File

```cmd
notepad .env
```

Update these settings:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
API_PORT=8003
```

Save and close.

---

## Step 2: Start Redis (If Not Running)

Check if Redis is running:

```cmd
docker ps | findstr "agentichr-redis"
```

If not running, start it:

```cmd
cd ..\orchestrator-agent
docker-compose up -d redis
cd ..\provisioning-agent
```

Test Redis connection:

```cmd
docker exec -it agentichr-redis redis-cli ping
```

Should output: `PONG`

---

## Step 3: Start Provisioning Agent

### Using the .bat Script (Recommended)

```cmd
start.bat
```

This will:
- Activate virtual environment automatically
- Start the agent on port 8003
- Show logs in the console

### Manual Start (Alternative)

```cmd
venv\Scripts\activate.bat
python -m src.main
```

You should see:

```
========================================
🚀 Provisioning Agent Starting
========================================
API: http://0.0.0.0:8003
Redis: localhost:6379
```

---

## Step 4: Test Provisioning Agent

### Quick Test (Automated)

Open a **new Command Prompt** window:

```cmd
cd C:\AgenticHR\provisioning-agent
test_provisioning.bat
```

### Manual Tests

#### Test 1: Health Check

```cmd
curl http://localhost:8003/api/v1/health
```

Expected output:
```json
{
  "status": "healthy",
  "agent": "provisioning_agent",
  "redis_connected": true,
  "version": "1.0.0"
}
```

#### Test 2: Status Check

```cmd
curl http://localhost:8003/api/v1/status
```

Expected output:
```json
{
  "agent": "provisioning_agent",
  "mode": "deterministic",
  "ai_enabled": false,
  "supported_task_types": [...]
}
```

#### Test 3: View API Docs

Open in browser:
- http://localhost:8003/docs

---

## Step 5: Test Task Execution

### Create Test Request File

Create a file `test_task.json`:

```cmd
notepad test_task.json
```

Paste this content:

```json
{
  "workflow_id": "WF_test_001",
  "tenant_id": "acme_corp",
  "task": {
    "task_id": "task_hr_001",
    "task_type": "create_hr_record",
    "payload": {
      "employee_name": "John Doe",
      "employee_email": "john.doe@acme.com",
      "role": "Software Engineer",
      "department": "Engineering",
      "start_date": "2026-03-01"
    },
    "priority": 5,
    "retry_count": 0
  }
}
```

Save and close.

### Execute Task via API

```cmd
curl -X POST http://localhost:8003/api/v1/execute-task ^
  -H "Content-Type: application/json" ^
  -d @test_task.json
```

**Note:** This will fail if n8n is not running (expected). The agent will return an error but continue running.

---

## Step 6: Integration Test with Redis

### Send Message via Redis Stream

```cmd
docker exec -it agentichr-redis redis-cli XADD agent_stream:provisioning_agent "*" message "{\"message_id\":\"test_001\",\"workflow_id\":\"WF_test\",\"tenant_id\":\"acme\",\"from_agent\":\"orchestrator_agent\",\"to_agent\":\"provisioning_agent\",\"message_type\":\"task_request\",\"task\":{\"task_id\":\"task_001\",\"task_type\":\"create_hr_record\",\"payload\":{\"employee_name\":\"Test User\",\"employee_email\":\"test@acme.com\",\"role\":\"Engineer\",\"department\":\"IT\"},\"priority\":5,\"retry_count\":0}}"
```

Check Provisioning Agent console - you should see:

```
Received message test_001 from orchestrator_agent
Processing task task_001 (type: create_hr_record)
```

---

## Full Workflow Test (All Agents)

If you have all agents set up, test the complete flow:

### Terminal 1: Start Guide Agent
```cmd
cd C:\AgenticHR\agentic-rag
venv\Scripts\activate.bat
python main.py
```

### Terminal 2: Start Orchestrator Agent
```cmd
cd C:\AgenticHR\orchestrator-agent
venv\Scripts\activate.bat
python -m src.main
```

### Terminal 3: Start Liaison Agent
```cmd
cd C:\AgenticHR\liaison-agent
venv\Scripts\activate.bat
python -m src.main
```

### Terminal 4: Start Provisioning Agent
```cmd
cd C:\AgenticHR\provisioning-agent
start.bat
```

### Test Complete Flow

In a new terminal:

```cmd
cd C:\AgenticHR\liaison-agent
curl -X POST http://localhost:8002/api/v1/message ^
  -H "Content-Type: application/json" ^
  -d "{\"tenant_id\":\"acme_corp\",\"user_id\":\"user_123\",\"message\":\"Onboard John Doe as Software Engineer\"}"
```

---

## Troubleshooting

### Issue: "curl: command not found"

**Solution 1:** Use Windows 10/11 built-in curl (available by default)

**Solution 2:** Install curl from https://curl.se/windows/

**Solution 3:** Use PowerShell's `Invoke-RestMethod` instead:

```cmd
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:8003/api/v1/health'"
```

### Issue: Port 8003 already in use

**Check what's using the port:**
```cmd
netstat -ano | findstr :8003
```

**Change port in .env:**
```cmd
notepad .env
REM Change API_PORT=8003 to API_PORT=8004
```

### Issue: Redis connection failed

**Check Redis is running:**
```cmd
docker ps
```

**Check Redis connection:**
```cmd
docker exec -it agentichr-redis redis-cli ping
```

**If not running:**
```cmd
cd ..\orchestrator-agent
docker-compose up -d redis
```

### Issue: Virtual environment activation fails

**Make sure you're in the right directory:**
```cmd
cd C:\AgenticHR\provisioning-agent
dir venv
```

**Recreate virtual environment:**
```cmd
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

## Useful Commands

### Check if Agent is Running

```cmd
netstat -ano | findstr :8003
```

### View Logs

```cmd
type logs\provisioning.log
```

### View Last 20 Lines of Logs

```cmd
powershell -Command "Get-Content logs\provisioning.log -Tail 20"
```

### Stop Agent

Press `Ctrl+C` in the terminal where the agent is running.

### Check Redis Streams

```cmd
REM Check provisioning stream exists
docker exec -it agentichr-redis redis-cli EXISTS agent_stream:provisioning_agent

REM View stream info
docker exec -it agentichr-redis redis-cli XINFO STREAM agent_stream:provisioning_agent

REM List all streams
docker exec -it agentichr-redis redis-cli KEYS agent_stream:*
```

### Clear Task Cache

```cmd
curl -X DELETE http://localhost:8003/api/v1/cache
```

---

## Daily Workflow

### Start Everything

```cmd
REM Terminal 1 - Provisioning Agent
cd C:\AgenticHR\provisioning-agent
start.bat

REM Terminal 2 - Other agents (if needed)
cd C:\AgenticHR\orchestrator-agent
start.ps1
```

### Stop Everything

- Press `Ctrl+C` in each terminal
- Or close the terminal windows

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Guide Agent | 8000 | http://localhost:8000 |
| Orchestrator | 8001 | http://localhost:8001 |
| Liaison Agent | 8002 | http://localhost:8002 |
| **Provisioning** | **8003** | **http://localhost:8003** |
| n8n | 5678 | http://localhost:5678 |
| Redis | 6379 | N/A (internal) |

---

## Quick Reference

```cmd
REM Setup (one time)
cd C:\AgenticHR\provisioning-agent
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
notepad .env

REM Start agent
start.bat

REM Test agent (new terminal)
test_provisioning.bat

REM Check health
curl http://localhost:8003/api/v1/health

REM View logs
type logs\provisioning.log

REM Stop agent
Ctrl+C
```

---

**That's it! You're ready to use the Provisioning Agent from Command Prompt.** 🚀
