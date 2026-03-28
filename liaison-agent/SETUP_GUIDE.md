# Liaison Agent - Setup Complete!

## ✅ What Was Done

The Liaison Agent has been successfully reorganized into a separate folder structure at:
**`C:\AgenticHR\liaison-agent\`**

### Directory Structure Created

```
C:\AgenticHR\liaison-agent\
├── src\
│   ├── agent\
│   │   ├── __init__.py
│   │   └── liaison.py              # Core agent with Gemini integration
│   ├── api\
│   │   ├── __init__.py
│   │   └── main.py                 # FastAPI application (6 endpoints)
│   ├── config\
│   │   ├── __init__.py
│   │   └── settings.py             # Liaison-specific settings
│   ├── messaging\
│   │   ├── __init__.py
│   │   └── redis_client.py         # Redis MCP integration
│   ├── schemas\
│   │   ├── __init__.py
│   │   ├── liaison_message.py      # API schemas
│   │   └── mcp_message.py          # MCP protocol schemas
│   └── __init__.py
├── logs\                            # Log directory
├── test_liaison.py                  # Comprehensive test suite
├── verify_liaison.py                # Setup verification script
├── start_liaison.bat               # ✨ CMD start script
├── setup.bat                       # ✨ CMD setup script
├── verify_liaison.bat              # ✨ CMD verify script
├── requirements.txt                 # All dependencies
├── .env.template                    # Environment configuration template
└── README.md                        # Complete documentation
```

### Key Changes from Original

1. **Separate Folder**: Moved from `orchestrator-agent/` to standalone `liaison-agent/`
2. **CMD Scripts**: Converted PowerShell (.ps1) to CMD batch files (.bat) for conda
3. **Updated Imports**: All imports now use `src.*` relative to liaison-agent
4. **Conda Environment**: Scripts use "agenticHR" conda environment
5. **Fixed API Path**: API file renamed to `main.py` for consistency
6. **Port 8002**: Configured to run on port 8002 (separate from orchestrator on 8001)

## 🚀 Quick Start Guide

### Method 1: Using CMD Prompt Directly (Recommended)

#### Step 1: Open Command Prompt and Navigate to Folder

```cmd
cd C:\AgenticHR\liaison-agent
```

#### Step 2: Activate Conda Environment

```cmd
conda activate agenticHR
```

#### Step 3: Install Dependencies

```cmd
pip install -r requirements.txt
```

#### Step 4: Create Environment File

```cmd
copy .env.template .env
```

Then edit `.env` file and set:
- `GOOGLE_API_KEY=your_actual_google_api_key_here`
- Other settings (Redis host, etc.)

#### Step 5: Verify Setup

```cmd
python verify_liaison.py
```

This checks:
- Python version (3.10+)
- Required files exist
- Dependencies installed
- Environment variables configured
- Imports working
- Redis connection (optional)

#### Step 6: Start Liaison Agent

```cmd
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

Agent will start on: **http://localhost:8002**

API Documentation: **http://localhost:8002/docs**

---

### Method 2: Using Batch Files (Optional)

If you prefer, you can use the provided batch files:

```cmd
:: Install dependencies
setup.bat

:: Verify setup
verify_liaison.bat

:: Start agent
start_liaison.bat
```

Note: Batch files will automatically activate the agenticHR conda environment

## 📋 Available Commands

### Direct CMD Commands (Recommended)

Make sure conda environment is activated first: `conda activate agenticHR`

| Command | Purpose |
|---------|---------|------
| `pip install -r requirements.txt` | Install all dependencies |
| `python verify_liaison.py` | Verify setup is correct |
| `python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload` | Start the Liaison Agent |
| `python test_liaison.py` | Run comprehensive tests |

### Batch File Commands (Optional)

These automatically activate the conda environment:

| Command | Purpose |
|---------|---------|------
| `setup.bat` | Install all dependencies |
| `verify_liaison.bat` | Verify setup is correct |
| `start_liaison.bat` | Start the Liaison Agent |
| `test_liaison.bat` | Run comprehensive tests |

## 🔧 Configuration

### Environment Variables (.env)

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Redis (required for production)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API Settings
API_HOST=0.0.0.0
API_PORT=8002
API_WORKERS=1

# Agent Settings
AGENT_TYPE=liaison_agent
AGENT_NAME=Liaison Agent

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🧪 Testing

### Run All Tests
```cmd
conda activate agenticHR
python test_liaison.py
```

### Test Suite Includes:
1. ✅ Policy Query Classification
2. ✅ Task Request Classification
3. ✅ Approval Response Handling
4. ✅ Missing Information Detection
5. ✅ Multi-turn Conversation Context
6. ✅ MCP Message Creation
7. ✅ Guide Response Processing
8. ✅ Approval Request Formatting

## 📡 API Endpoints

### POST /message
Process user message and classify intent

### POST /approval
Process approval/rejection decision

### POST /guide-response
Receive policy response from Guide Agent

### POST /approval-request
Receive approval request from Orchestrator

### DELETE /conversation/{tenant_id}/{workflow_id}
Clear conversation history

### GET /health
Health check endpoint

## 🔗 Integration with Other Agents

### Communication Flow

```
User → Liaison Agent (Port 8002)
  ↓
  ├─→ Guide Agent (via Redis) for policy queries
  └─→ Orchestrator Agent (via Redis) for task requests
```

### Redis Streams
- **Publishes to**: `guide_agent:inbox`, `orchestrator_agent:inbox`
- **Subscribes to**: `liaison_agent:inbox`

## ✨ What's Different from Orchestrator

| Aspect | Orchestrator Agent | Liaison Agent |
|--------|-------------------|---------------|
| Location | `orchestrator-agent/` | `liaison-agent/` |
| Port | 8001 | 8002 |
| Purpose | Workflow orchestration | User interaction & routing |
| LLM | Various | Google Gemini 2.5 |
| API File | `src/main.py` | `src/api/main.py` |
| Scripts | PowerShell + CMD | CMD only |

## 🎯 Import Resolution

All imports are now relative to `liaison-agent/` folder:

```python
from src.agent.liaison import liaison_agent
from src.config.settings import settings
from src.schemas.liaison_message import UserMessage
from src.schemas.mcp_message import AgentType
from src.messaging.redis_client import redis_client
```

**No conflicts** with orchestrator-agent imports!

## 📝 Dependencies

All dependencies are in `requirements.txt`:

- **fastapi** - REST API framework
- **uvicorn** - ASGI server
- **google-generativeai** - Gemini LLM
- **redis** - Message transport
- **pydantic** - Data validation
- **pydantic-settings** - Settings management
- **loguru** - Logging
- **python-dotenv** - Environment variables
- **httpx** - HTTP client for testing

## 🐛 Troubleshooting

### "Failed to activate conda environment"
```cmd
conda env list  # Check if agenticHR exists
conda create -n agenticHR python=3.10  # Create if missing
```

### "GOOGLE_API_KEY not set"
```cmd
# Edit .env file and add your API key
notepad .env
```

### "Port 8002 already in use"
```cmd
netstat -an | findstr 8002  # Check what's using the port
# Change API_PORT in .env if needed
```

### "Redis connection failed"
```cmd
# Start Redis server or update REDIS_HOST in .env
# Agent works without Redis for testing
```

## 📚 Documentation

- **README.md** - Full documentation
- **SETUP_GUIDE.md** - This guide
- **API Docs** - http://localhost:8002/docs (when running)

## ✅ Verification Checklist

- [ ] Conda environment "agenticHR" exists
- [ ] Dependencies installed via `setup.bat`
- [ ] `.env` file created with GOOGLE_API_KEY
- [ ] Verification passes: `verify_liaison.bat`
- [ ] Agent starts successfully: `start_liaison.bat`
- [ ] Tests pass: `python test_liaison.py`
- [ ] API accessible: http://localhost:8002/docs

## 🎉 Success!

Your Liaison Agent is now:
- ✅ In a separate folder (`liaison-agent/`)
- ✅ Using CMD batch scripts (not PowerShell)
- ✅ Configured for "agenticHR" conda environment
- ✅ Import-conflict free with orchestrator-agent
- ✅ Ready to integrate with AgenticHR system

---

**Next Steps:**
1. Open CMD and run: `conda activate agenticHR`
2. Navigate to folder: `cd C:\AgenticHR\liaison-agent`
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` file from `.env.template` and add your `GOOGLE_API_KEY`
5. Verify: `python verify_liaison.py`
6. Start agent: `python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload`
7. Test at http://localhost:8002/docs

**Prefer batch files?** You can use `setup.bat`, `verify_liaison.bat`, and `start_liaison.bat` instead.

**Questions?** Check README.md or logs in `logs/liaison.log`
