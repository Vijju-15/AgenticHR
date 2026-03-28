# Orchestrator Agent

Central workflow orchestration agent for AgenticHR system.

## Setup

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```powershell
cp .env.example .env
```

Required configurations:
- **GOOGLE_API_KEY**: Get from Google AI Studio (https://aistudio.google.com/app/apikey)
- **POSTGRES_PASSWORD**: Set your PostgreSQL password
- **DATABASE_URL**: Update with your credentials

### 3. Setup PostgreSQL

```powershell
# Install PostgreSQL (if not already installed)
# Download from: https://www.postgresql.org/download/windows/

# Create database
psql -U postgres
CREATE DATABASE agentichr;
\q
```

### 4. Setup Redis

```powershell
# Option 1: Install Redis on Windows
# Download from: https://github.com/microsoftarchive/redis/releases

# Option 2: Use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### 5. Run the Service

```powershell
# Development mode
python -m uvicorn src.main:app --reload --port 8001

# Production mode
python src/main.py
```

## Docker Deployment

```powershell
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f orchestrator-agent

# Stop services
docker-compose down
```

## API Endpoints

- `GET /health` - Health check
- `POST /onboarding/initiate` - Initiate onboarding workflow
- `POST /tasks/result` - Receive task results from agents
- `GET /workflows/{workflow_id}` - Get workflow details
- `GET /workflows` - List workflows

## Testing

```powershell
# Test onboarding initiation
curl -X POST http://localhost:8001/onboarding/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme_corp",
    "employee_id": "EMP001",
    "employee_name": "John Doe",
    "employee_email": "john@acme.com",
    "role": "Software Engineer",
    "department": "Engineering",
    "start_date": "2026-03-01",
    "manager_email": "manager@acme.com"
  }'

# Check workflow status
curl http://localhost:8001/workflows/WF_xxx
```

## Architecture

```
HR Admin → POST /onboarding/initiate
              ↓
    Orchestrator Agent (Gemini 2.5)
              ↓
    Decompose into tasks
              ↓
    Delegate via Redis Streams
              ↓
    [Provisioning | Scheduler | Liaison | Guide]
              ↓
    Receive task results
              ↓
    Update workflow state
              ↓
    Complete or retry
```

## Gemini Model

The orchestrator uses **Gemini 2.0 Flash (Experimental)** for:
- Task decomposition
- Workflow planning
- Decision making
- Approval logic

All outputs are structured JSON for MCP-style communication.
