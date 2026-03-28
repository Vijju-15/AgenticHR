# 🚀 Production Setup Guide - Agentic RAG with n8n

## Prerequisites
- Docker Desktop installed and running
- Python 3.9+ with conda environment
- n8n installed (or running via Docker)
- API keys configured

---

## Step 1: Start Qdrant Vector Database

```powershell
# Pull and run Qdrant
docker run -d -p 6333:6333 -p 6334:6334 `
  -v ${PWD}/qdrant_storage:/qdrant/storage `
  --name qdrant `
  qdrant/qdrant
```

**Verify it's running:**
```powershell
# Check container status
docker ps | findstr qdrant

# Test the API
curl http://localhost:6333/collections
```

---

## Step 2: Configure Environment Variables

Your `.env` file is already set up. Verify these key variables:

```env
GOOGLE_API_KEY=your-google-api-key-here
QDRANT_HOST=localhost
QDRANT_PORT=6333
API_PORT=8000
```

---

## Step 3: Activate Conda Environment & Install Dependencies

```powershell
# Activate conda environment
C:/Users/lsnba/anaconda3/Scripts/activate
conda activate agentic

# Install/verify all dependencies
pip install -r requirements.txt
```

---

## Step 4: Ingest Documents into Vector Database

```powershell
# Set environment and run ingestion
$env:GOOGLE_API_KEY="your-google-api-key-here"

# Run the multi-tenant ingestion script
python -m src.rag.multi_tenant_ingestion
```

**This will:**
- Create collections for each company
- Ingest all documents from `data/knowledge_base/`
- Set up employee databases

---

## Step 5: Start the FastAPI Server

```powershell
# Start the API server
cd C:\agentic-rag
$env:GOOGLE_API_KEY="your-google-api-key-here"

# Activate conda and run
C:/Users/lsnba/anaconda3/Scripts/activate
conda activate agentic

# Start uvicorn server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test the API:**
```powershell
# Test health endpoint
curl http://localhost:8000/health

# Test query endpoint
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"What is the leave policy?\", \"company_id\": \"acme_corp\"}'
```

---

## Step 6: Start n8n

### Option A: Run n8n via Docker (Recommended)

```powershell
# Run n8n with Docker
docker run -d -p 5678:5678 `
  -v ${PWD}/n8n_data:/home/node/.n8n `
  --name n8n `
  n8nio/n8n
```

### Option B: Run n8n locally (if already installed)

```powershell
n8n start
```

**Access n8n:**
Open browser: `http://localhost:5678`

---

## Step 7: Import the Workflow into n8n

1. **Open n8n** at `http://localhost:5678`

2. **Import Workflow:**
   - Click **"Workflows"** → **"Add workflow"** → **"Import from file"**
   - Select: `C:\agentic-rag\n8n_workflows\agentic_rag_production_workflow_fixed.json`
   - Click **"Import"**

3. **Configure the API URL:**
   - Click on **"Call Agentic RAG API"** node
   - Update URL if needed (should be `http://localhost:8000/chat`)
   - If n8n is in Docker and API is on host, use: `http://host.docker.internal:8000/chat`

4. **Configure Slack (Optional):**
   - Click **"Send to Slack"** node
   - Add your Slack credentials
   - Select the channel

5. **Configure Google Sheets (Optional):**
   - Click **"Log to Google Sheets"** node
   - Add Google Sheets credentials
   - Set environment variable `GOOGLE_SHEETS_DOC_ID` or replace in the node

---

## Step 8: Test the Workflow

### 8.1: Add Test Data to Manual Trigger

1. Click on **"When chat message received"** node
2. Click **"Execute node"** or **"Test step"**
3. In the input panel, add this JSON:

```json
{
  "message": "What is the leave policy?",
  "company_id": "acme_corp",
  "user_id": "john.doe",
  "session_id": "test_session_001"
}
```

### 8.2: Execute the Workflow

1. Click **"Execute Workflow"** button (top right)
2. Watch the nodes execute one by one
3. Check the output at each node

### 8.3: Expected Results

- ✅ **Validate Input:** Formats and validates data
- ✅ **Call Agentic RAG API:** Returns AI response with sources
- ✅ **Check Response Status:** Routes to success/error path
- ✅ **Format Success Response:** Structures the response
- ✅ **Log Interaction:** Logs to console
- ✅ **Send to Slack:** Posts to Slack channel (if enabled)
- ✅ **Log to Google Sheets:** Saves to spreadsheet (if enabled)

---

## Step 9: Production Deployment

### For Production API:

```powershell
# Use production server (not --reload)
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker Compose (Complete Stack):

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - qdrant
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    volumes:
      - ./n8n_data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=changeme
```

**Run with Docker Compose:**
```powershell
docker-compose up -d
```

---

## Step 10: Using the Workflow

### Via n8n UI:
1. Execute manually with test data
2. Watch execution in real-time
3. View outputs and logs

### Via Webhook (for external integrations):

1. **Enable Webhook Trigger** in n8n:
   - Add a Webhook node at the start
   - Get the webhook URL (e.g., `http://localhost:5678/webhook/agentic-rag`)

2. **Send requests:**
```powershell
curl -X POST http://localhost:5678/webhook/agentic-rag `
  -H "Content-Type: application/json" `
  -d '{
    "message": "How do I request leave?",
    "company_id": "acme_corp",
    "user_id": "jane.smith"
  }'
```

---

## Troubleshooting

### API not responding:
```powershell
# Check if API is running
curl http://localhost:8000/health

# Check logs
Get-Content logs\hr_assistant.log -Tail 50
```

### Qdrant connection issues:
```powershell
# Check Qdrant status
docker logs qdrant

# Test connection
curl http://localhost:6333/collections
```

### n8n workflow errors:
- Check node configurations
- Verify API URL (use `host.docker.internal` if n8n is in Docker)
- Check credentials for Slack/Google Sheets

### Environment variable issues:
```powershell
# Verify environment
$env:GOOGLE_API_KEY

# Re-set if needed
$env:GOOGLE_API_KEY="your-google-api-key-here"
```

---

## Quick Start Commands (All in One)

```powershell
# 1. Start Qdrant
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant

# 2. Set environment
$env:GOOGLE_API_KEY="your-google-api-key-here"

# 3. Activate conda
C:/Users/lsnba/anaconda3/Scripts/activate ; conda activate agentic

# 4. Ingest data (first time only)
python -m src.rag.multi_tenant_ingestion

# 5. Start API
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 6. In another terminal - Start n8n
docker run -d -p 5678:5678 --name n8n n8nio/n8n

# 7. Open browser: http://localhost:5678 and import workflow
```

---

## Testing Queries

Try these test queries in n8n:

```json
{
  "message": "What is the leave policy?",
  "company_id": "acme_corp",
  "user_id": "test_user"
}
```

```json
{
  "message": "Book a meeting for tomorrow at 2pm",
  "company_id": "acme_corp",
  "user_id": "john.doe"
}
```

```json
{
  "message": "Request 3 days leave starting next Monday",
  "company_id": "acme_corp",
  "user_id": "jane.smith"
}
```

---

## 🎉 You're Ready!

Your Agentic RAG system is now running and integrated with n8n for production use!

**Architecture:**
```
n8n (Port 5678) 
  ↓ HTTP POST
FastAPI (Port 8000)
  ↓ Vector Search
Qdrant (Port 6333)
  ↓ LLM Calls
Google Gemini API
```

