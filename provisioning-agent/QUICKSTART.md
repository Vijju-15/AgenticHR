# Provisioning Agent - Quick Start Guide

Get the Provisioning Agent running in 5 minutes.

## Prerequisites

✅ **Python 3.9+** installed  
✅ **Redis** running (Docker: `agentichr-redis` on port 6379)  
✅ **n8n** running (optional for full integration, on port 5678)

---

## Step 1: Setup

Open PowerShell in the `provisioning-agent` folder:

```powershell
.\setup.ps1
```

This will:
- Create Python virtual environment
- Install dependencies
- Create `.env` file from template

---

## Step 2: Configure

Edit `.env` file:

```env
# Minimal configuration
REDIS_HOST=localhost
REDIS_PORT=6379
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
```

**Note:** If Redis is in Docker (default):
- Keep `REDIS_HOST=localhost`
- Keep `REDIS_PORT=6379`

---

## Step 3: Start

```powershell
.\start.ps1
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

## Step 4: Verify

Open another terminal and test:

```powershell
# Test health
curl http://localhost:8003/api/v1/health

# Test status
curl http://localhost:8003/api/v1/status
```

Or run the test script:

```powershell
.\test_provisioning.bat
```

---

## Step 5: View API Docs

Open in browser:
- **Swagger UI**: http://localhost:8003/docs
- **Root**: http://localhost:8003

---

## Testing Task Execution

### Option 1: Via API (Direct)

```powershell
# PowerShell
$body = @{
    workflow_id = "WF_test_001"
    tenant_id = "acme_corp"
    task = @{
        task_id = "task_hr_001"
        task_type = "create_hr_record"
        payload = @{
            employee_name = "John Doe"
            employee_email = "john.doe@acme.com"
            role = "Software Engineer"
            department = "Engineering"
            start_date = "2026-03-01"
        }
        priority = 5
        retry_count = 0
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8003/api/v1/execute-task" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

### Option 2: Via Redis Stream (Production)

The agent automatically listens to Redis stream: `agent_stream:provisioning_agent`

Messages are sent by the Orchestrator Agent.

---

## Quick Troubleshooting

### ❌ "Redis connection failed"

**Fix:**
```powershell
# Check if Redis Docker container is running
docker ps | Select-String "agentichr-redis"

# Start Redis if needed
docker start agentichr-redis

# Or run from orchestrator-agent folder:
docker-compose up -d redis
```

### ❌ "Virtual environment not found"

**Fix:**
```powershell
# Run setup first
.\setup.ps1
```

### ❌ "n8n webhook call failed"

**Expected behavior** if n8n is not running. The agent will return an error but continue running.

**To fix (optional):**
- Install and run n8n: `npm install -g n8n && n8n start`
- Configure webhooks in n8n (see n8n documentation)

---

## Next Steps

1. **Set up n8n workflows** - Create webhook endpoints for provisioning tasks
2. **Integrate with Orchestrator** - Start Orchestrator Agent to delegate tasks
3. **Monitor logs** - Check `logs/provisioning.log` for detailed execution logs
4. **Configure multi-tenancy** - Set up tenant-specific configurations

---

## Stopping the Agent

Press `Ctrl+C` in the terminal where the agent is running.

---

## Useful Commands

```powershell
# Check Redis connection
docker exec -it agentichr-redis redis-cli ping

# View Redis stream
docker exec -it agentichr-redis redis-cli XINFO STREAM agent_stream:provisioning_agent

# Check API health
curl http://localhost:8003/api/v1/health

# View logs
Get-Content logs\provisioning.log -Tail 50 -Wait
```

---

## Port Reference

- **8003** - Provisioning Agent API
- **6379** - Redis
- **5678** - n8n (optional)
- **8001** - Orchestrator Agent (optional)
- **8002** - Liaison Agent (optional)

---

## Need Help?

- Check `logs/provisioning.log` for errors
- See full README.md for detailed documentation
- Check Redis connection is healthy
- Ensure port 8003 is not in use

---

**You're all set! 🚀**

The Provisioning Agent is now running and ready to execute provisioning tasks.
