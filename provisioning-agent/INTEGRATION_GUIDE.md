# Provisioning Agent - Integration Guide

This guide explains how to integrate the Provisioning Agent with the existing AgenticHR system.

## System Overview

```
┌─────────────────┐
│ Liaison Agent   │ ← User conversations
│   (Port 8002)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Orchestrator    │ ← Workflow planning & delegation
│   (Port 8001)   │
└────────┬────────┘
         │
         ├──────────► Guide Agent (Port 8000) ← Policy RAG
         │
         ├──────────► Provisioning Agent (Port 8003) ← YOU ARE HERE
         │
         └──────────► Scheduler Agent (TBD)
                      
         ▲
         │
   Redis Streams
```

## Integration Steps

### Step 1: Ensure Redis is Running

The Provisioning Agent requires Redis for inter-agent communication.

```powershell
# Check if Redis is running
docker ps | Select-String "agentichr-redis"

# If not running, start it (from orchestrator-agent folder)
cd ..\orchestrator-agent
docker-compose up -d redis
cd ..\provisioning-agent
```

Verify:
```powershell
docker exec -it agentichr-redis redis-cli ping
# Should output: PONG
```

### Step 2: Setup Provisioning Agent

```powershell
# Run setup
.\setup.ps1

# Edit .env file
# Ensure REDIS_HOST and REDIS_PORT match your Redis instance
notepad .env
```

### Step 3: Start Provisioning Agent

```powershell
.\start.ps1
```

The agent will:
1. Connect to Redis
2. Create consumer group `provisioning_agent_group`
3. Listen on stream `agent_stream:provisioning_agent`
4. Start REST API on port 8003

### Step 4: Test Standalone

```powershell
# In a new terminal
.\test_provisioning.bat
```

Or test via API:
```powershell
# Test health
curl http://localhost:8003/api/v1/health

# Test status
curl http://localhost:8003/api/v1/status
```

### Step 5: Test with Orchestrator (Optional)

If you have the Orchestrator Agent running, you can test end-to-end integration.

**From Orchestrator terminal:**

```powershell
# Send a test message to Provisioning Agent via Redis
docker exec -it agentichr-redis redis-cli XADD agent_stream:provisioning_agent "*" message '{\"message_id\":\"test_001\",\"workflow_id\":\"WF_test\",\"tenant_id\":\"acme\",\"from_agent\":\"orchestrator_agent\",\"to_agent\":\"provisioning_agent\",\"message_type\":\"task_request\",\"task\":{\"task_id\":\"task_001\",\"task_type\":\"create_hr_record\",\"payload\":{\"employee_name\":\"Test User\",\"employee_email\":\"test@acme.com\",\"role\":\"Engineer\",\"department\":\"IT\"},\"priority\":5,\"retry_count\":0}}'
```

**Check Provisioning Agent logs:**

You should see:
```
Received message test_001 from orchestrator_agent
Processing task task_001 (type: create_hr_record)
```

---

## Integration with n8n

### Setup n8n (Optional but Recommended)

Install n8n:
```powershell
# Install n8n globally
npm install -g n8n

# Start n8n
n8n start
```

Access n8n: http://localhost:5678

### Create Webhook Workflows in n8n

For each provisioning task type, create a webhook workflow:

#### Example: Create HR Record Webhook

1. **Create new workflow** in n8n
2. **Add Webhook node**
   - Method: POST
   - Path: `create-hr-record`
3. **Add HTTP Response node**
   - Status Code: 200
   - Response Body:
     ```json
     {
       "hris_record_id": "{{ $json.tenant_id }}-{{ $timestamp }}",
       "employee_id": "EMP-{{ $timestamp }}",
       "record_url": "https://hris.example.com/employees/{{ $json.tenant_id }}",
       "created_at": "{{ $now }}",
       "system": "mock-hris"
     }
     ```
4. **Save and activate**

Webhook URL will be: `http://localhost:5678/webhook/create-hr-record`

Repeat for other task types:
- `/webhook/create-it-ticket`
- `/webhook/assign-access`
- `/webhook/generate-id`
- `/webhook/create-email`
- `/webhook/request-laptop`

### Test n8n Integration

```powershell
# Test webhook directly
$body = @{
    tenant_id = "acme_corp"
    employee_data = @{
        employee_name = "John Doe"
        employee_email = "john.doe@acme.com"
        role = "Software Engineer"
        department = "Engineering"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5678/webhook/create-hr-record" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

---

## End-to-End Test Flow

### Scenario: New Employee Onboarding

1. **Liaison Agent** receives user message: "Onboard John Doe as Software Engineer"
2. **Liaison Agent** detects onboarding intent, sends to Orchestrator
3. **Orchestrator Agent** creates workflow, delegates task to Provisioning Agent
4. **Provisioning Agent** receives task via Redis stream
5. **Provisioning Agent** validates payload
6. **Provisioning Agent** calls n8n webhook
7. **n8n** creates HRIS record (via integration)
8. **n8n** returns success with record ID
9. **Provisioning Agent** sends result back to Orchestrator via Redis
10. **Orchestrator** updates workflow state, proceeds to next task

---

## Monitoring Integration

### Check All Agents are Running

```powershell
# Guide Agent
curl http://localhost:8000/health

# Orchestrator Agent
curl http://localhost:8001/api/v1/health

# Liaison Agent
curl http://localhost:8002/api/v1/health

# Provisioning Agent
curl http://localhost:8003/api/v1/health
```

### Check Redis Streams

```powershell
# List all streams
docker exec -it agentichr-redis redis-cli KEYS "agent_stream:*"

# Check provisioning agent stream
docker exec -it agentichr-redis redis-cli XINFO STREAM agent_stream:provisioning_agent

# Check consumer groups
docker exec -it agentichr-redis redis-cli XINFO GROUPS agent_stream:provisioning_agent
```

---

## Troubleshooting Integration

### Issue: Provisioning Agent not receiving messages

**Check:**
1. Redis connection:
   ```powershell
   curl http://localhost:8003/api/v1/health
   # redis_connected should be true
   ```

2. Stream exists:
   ```powershell
   docker exec -it agentichr-redis redis-cli EXISTS agent_stream:provisioning_agent
   # Should return 1
   ```

3. Consumer group exists:
   ```powershell
   docker exec -it agentichr-redis redis-cli XINFO GROUPS agent_stream:provisioning_agent
   # Should list provisioning_agent_group
   ```

### Issue: n8n webhook calls failing

**Check:**
1. n8n is running:
   ```powershell
   curl http://localhost:5678/healthz
   ```

2. Webhook URL is correct in `.env`:
   ```
   N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
   ```

3. Webhook exists in n8n:
   - Open n8n UI: http://localhost:5678
   - Check workflow is active
   - Test webhook directly

### Issue: Port conflicts

If port 8003 is already in use:

Edit `.env`:
```
API_PORT=8004  # or any available port
```

Restart agent:
```powershell
# Press Ctrl+C to stop
.\start.ps1
```

---

## Multi-Tenant Configuration

### Per-Tenant Redis Streams (Future)

Currently, all tenants share the same stream. For production multi-tenancy:

1. **Option A:** Tenant-scoped streams
   - `agent_stream:provisioning_agent:acme_corp`
   - `agent_stream:provisioning_agent:techstart_inc`

2. **Option B:** Message filtering
   - Single stream, filter by `tenant_id` in agent

### Per-Tenant n8n Workflows (Future)

Create tenant-specific webhook endpoints:
- `/webhook/acme/create-hr-record`
- `/webhook/techstart/create-hr-record`

Update agent to route based on `tenant_id`.

---

## Production Deployment Checklist

- [ ] Redis is running in production (not localhost)
- [ ] n8n is running in production (not localhost)
- [ ] Update `.env` with production URLs
- [ ] Enable authentication on Redis (set REDIS_PASSWORD)
- [ ] Enable authentication on n8n (set N8N_API_KEY)
- [ ] Use Uvicorn with multiple workers (set API_WORKERS)
- [ ] Set up log aggregation (ELK/Datadog)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure firewall rules (restrict ports)
- [ ] Use HTTPS for all webhooks
- [ ] Implement Redis cache persistence (for idempotency)
- [ ] Set up backup for Redis data

---

## Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Guide Agent | 8000 | Policy RAG queries |
| Orchestrator Agent | 8001 | Workflow planning |
| Liaison Agent | 8002 | User conversations |
| **Provisioning Agent** | **8003** | **Provisioning tasks** |
| n8n | 5678 | Workflow automation |
| Redis | 6379 | Message streaming |

---

## Next Steps

1. ✅ Provisioning Agent is running
2. ⏭️ Create n8n workflows for each task type
3. ⏭️ Test with Orchestrator Agent
4. ⏭️ Test full user journey (Liaison → Orchestrator → Provisioning)
5. ⏭️ Add real HRIS/IT system integrations in n8n
6. ⏭️ Build Scheduler Agent (for meeting scheduling)
7. ⏭️ Deploy to production

---

## Support

- Check `logs/provisioning.log` for detailed logs
- See README.md for full documentation
- See IMPLEMENTATION_SUMMARY.md for architecture details
- See QUICKSTART.md for quick setup

---

**🎉 Integration Complete!**

Your Provisioning Agent is now part of the AgenticHR multi-agent system.
