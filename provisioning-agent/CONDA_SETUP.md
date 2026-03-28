# Running Provisioning Agent with Conda Environment

Quick guide for running the Provisioning Agent using your **existing conda environment**.

---

## Prerequisites

✅ Conda environment (e.g., `agenticHR`) already created  
✅ Redis running (Docker container `agentichr-redis`)  
✅ Command Prompt

---

## Step 1: Activate Your Conda Environment

Open **Command Prompt**:

```cmd
conda activate agenticHR
```

You should see `(agenticHR)` prefix in your prompt.

---

## Step 2: Navigate to Provisioning Agent Folder

```cmd
cd C:\AgenticHR\provisioning-agent
```

---

## Step 3: Install Dependencies

```cmd
pip install -r requirements.txt
```

This installs the provisioning agent dependencies into your existing conda environment.

---

## Step 4: Create .env File

```cmd
copy .env.example .env
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

## Step 5: Check Redis is Running

```cmd
docker exec -it agentichr-redis redis-cli ping
```

Should output: `PONG`

If not running:
```cmd
cd ..\orchestrator-agent
docker-compose up -d redis
cd ..\provisioning-agent
```

---

## Step 6: Start Provisioning Agent

**Option 1: Simple (Recommended)**

```cmd
REM Make sure conda env is activated
conda activate agenticHR

REM Start agent
python -m src.main
```

**Option 2: Using Script**

```cmd
REM Make sure conda env is activated
conda activate agenticHR

REM Start agent
start-conda.bat
```

You should see:

```
========================================
🚀 Provisioning Agent Starting
========================================
API: http://0.0.0.0:8003
Redis: localhost:6379
n8n Webhooks: http://localhost:5678/webhook
========================================
```

---

## Step 7: Test It (New Command Prompt Window)

Open a **new Command Prompt** window:

```cmd
REM Activate conda env
conda activate agenticHR

REM Navigate to folder
cd C:\AgenticHR\provisioning-agent

REM Test health
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

### More Tests

```cmd
REM Test status
curl http://localhost:8003/api/v1/status

REM View API docs in browser
start http://localhost:8003/docs

REM Run automated tests
python test_provisioning.py
```

---

## Complete Workflow (Using Conda)

### Terminal 1: Guide Agent
```cmd
conda activate agenticHR
cd C:\AgenticHR\agentic-rag
python main.py
```

### Terminal 2: Orchestrator Agent
```cmd
conda activate agenticHR
cd C:\AgenticHR\orchestrator-agent
python -m src.main
```

### Terminal 3: Liaison Agent
```cmd
conda activate agenticHR
cd C:\AgenticHR\liaison-agent
python -m src.main
```

### Terminal 4: Provisioning Agent
```cmd
conda activate agenticHR
cd C:\AgenticHR\provisioning-agent
python -m src.main
```

---

## Quick Setup Script (One-Time)

If you want to use the setup script:

```cmd
REM Activate your conda environment first
conda activate agenticHR

REM Navigate to folder
cd C:\AgenticHR\provisioning-agent

REM Run conda-specific setup
setup-conda.bat
```

This will:
- Install dependencies into your conda environment
- Create .env file
- Create logs directory

---

## Daily Workflow

### Start Agent

```cmd
REM 1. Activate conda environment
conda activate agenticHR

REM 2. Navigate to folder
cd C:\AgenticHR\provisioning-agent

REM 3. Start agent
python -m src.main
```

### Test Agent (New Window)

```cmd
conda activate agenticHR
cd C:\AgenticHR\provisioning-agent
curl http://localhost:8003/api/v1/health
```

### Stop Agent

Press `Ctrl+C` in the terminal where the agent is running.

---

## Troubleshooting

### Issue: "No module named 'fastapi'" or similar

**Solution:** Install dependencies in your conda environment

```cmd
conda activate agenticHR
cd C:\AgenticHR\provisioning-agent
pip install -r requirements.txt
```

### Issue: "Conda not recognized"

**Solution:** Make sure conda is in your PATH or use Anaconda Prompt

```cmd
REM Option 1: Add conda to PATH (one time)
REM Add C:\Users\YourName\anaconda3\Scripts to PATH

REM Option 2: Use Anaconda Prompt instead of regular CMD
REM Search for "Anaconda Prompt" in Start Menu
```

### Issue: Wrong conda environment activated

**Check current environment:**
```cmd
conda info --envs
```

**Activate correct environment:**
```cmd
conda activate agenticHR
```

---

## Useful Commands

### Check Current Conda Environment

```cmd
conda info --envs
```

The active environment will have a `*` next to it.

### List Installed Packages in Conda Environment

```cmd
conda activate agenticHR
pip list
```

### Verify Dependencies

```cmd
conda activate agenticHR
python -c "import fastapi, redis, httpx, loguru; print('All dependencies installed!')"
```

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

## Summary

**One-time setup:**
```cmd
conda activate agenticHR
cd C:\AgenticHR\provisioning-agent
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

**Start agent:**
```cmd
conda activate agenticHR
cd C:\AgenticHR\provisioning-agent
python -m src.main
```

**Test agent:**
```cmd
curl http://localhost:8003/api/v1/health
```

**That's it!** 🚀

---

## No Virtual Environment Needed!

Since you're using conda, you don't need the `venv` folder at all. You can delete it if it exists:

```cmd
cd C:\AgenticHR\provisioning-agent
rmdir /s /q venv
```

Everything runs in your conda environment instead.
