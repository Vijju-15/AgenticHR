# Liaison Agent

Conversational router and intent detection agent for the AgenticHR multi-agent system.

## 📚 Documentation Guide

- **[GETTING_STARTED.md](GETTING_STARTED.md)** - ⚡ Quickest way to get running (2 minutes)
- **[CMD_QUICKSTART.md](CMD_QUICKSTART.md)** - All CMD commands for direct usage
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **This README** - Complete technical documentation

**Running in CMD?** Start with [GETTING_STARTED.md](GETTING_STARTED.md) - just 4 commands to get running!

## Overview

The Liaison Agent is the user-facing entry point for the AgenticHR system. It handles:

- **Intent Classification**: Detects user intent using Google Gemini 2.5
- **Routing**: Routes policy queries to Guide Agent
- **Delegation**: Delegates task requests to Orchestrator Agent  
- **Field Extraction**: Extracts structured data from natural language
- **Approvals**: Formats and processes approval requests/responses
- **Conversation Context**: Maintains multi-turn conversation history

## Architecture

```
┌─────────────┐
│    User     │
└─────┬───────┘
      │
      ▼
┌─────────────────────┐
│  Liaison Agent      │
│  (Port 8002)       │
│                     │
│ ┌─────────────────┐ │
│ │ Intent          │ │
│ │ Classification  │ │
│ └────────┬────────┘ │
│          │          │
│  ┌───────▼────────┐ │
│  │ Field          │ │
│  │ Extraction     │ │
│  └────────────────┘ │
└──────┬──────┬───────┘
       │      │
       ▼      ▼
   ┌─────┐  ┌──────────┐
   │Guide│  │Orchestr  │
   │Agent│  │ator Agent│
   └─────┘  └──────────┘
```

## Quick Start

### 1. Setup Environment

**Using CMD Prompt Directly:**

```cmd
:: Navigate to liaison-agent folder
cd C:\AgenticHR\liaison-agent

:: Activate conda environment
conda activate agenticHR

:: Install dependencies
pip install -r requirements.txt
```

**Or use the batch file:**
```cmd
setup.bat
```

### 2. Configure Environment

Create `.env` file from template:

```cmd
copy .env.template .env
```

Edit `.env` and set:
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `REDIS_HOST`: Redis server address (default: localhost)
- Other settings as needed

### 3. Verify Setup

**Using CMD Prompt:**
```cmd
conda activate agenticHR
python verify_liaison.py
```

**Or use the batch file:**
```cmd
verify_liaison.bat
```

### 4. Start Agent

**Using CMD Prompt:**
```cmd
conda activate agenticHR
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

**Or use the batch file:**
```cmd
start_liaison.bat
```

The agent will start on http://localhost:8002

## API Endpoints

### POST /message
Process incoming user message

**Request:**
```json
{
  "message": "I want to apply for leave from March 15 to March 20",
  "user_id": "emp_12345",
  "tenant_id": "acme_corp",
  "workflow_id": "optional_workflow_id",
  "user_name": "John Doe",
  "user_role": "employee",
  "metadata": {}
}
```

**Response:**
```json
{
  "response_text": "I'll process your leave request...",
  "intent_type": "task_request",
  "confidence_score": 0.95,
  "action_taken": "delegate_to_orchestrator",
  "workflow_id": "WF_acme_corp_emp12345_abc123",
  "metadata": {
    "reason": "Leave application request",
    "payload": {...}
  }
}
```

### POST /approval
Process approval/rejection response

**Request:**
```json
{
  "user_id": "manager_001",
  "tenant_id": "acme_corp",
  "workflow_id": "WF_acme_corp_emp001_abc123",
  "approval_status": "approved",
  "approver_note": "Approved as requested",
  "timestamp": "2026-01-15T10:30:00"
}
```

### POST /guide-response
Receive response from Guide Agent (internal)

### POST /approval-request
Receive approval request from Orchestrator (internal)

### DELETE /conversation/{tenant_id}/{workflow_id}
Clear conversation history

### GET /health
Health check endpoint

## Intent Types

- `policy_query`: Questions about policies/procedures
- `task_request`: Actionable requests (leave, meetings, etc.)
- `approval_response`: Approval/rejection decisions
- `general_query`: General questions/greetings
- `unknown`: Unable to classify

## Actions

- `route_to_guide`: Send to Guide Agent for policy info
- `delegate_to_orchestrator`: Send to Orchestrator for task execution
- `ask_clarification`: Request more information from user
- `acknowledge`: Simple acknowledgment

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `REDIS_HOST` | Redis server host | localhost |
| `REDIS_PORT` | Redis server port | 6379 |
| `API_PORT` | Agent API port | 8002 |
| `LOG_LEVEL` | Logging level | INFO |
| `ENVIRONMENT` | Environment (dev/prod) | development |

### Settings File

See [src/config/settings.py](src/config/settings.py) for all configuration options.

## Testing

### Run All Tests

**Using CMD Prompt:**
```cmd
conda activate agenticHR
python test_liaison.py
```

**Or use the batch file:**
```cmd
test_liaison.bat
```

### Test Individual Features
```python
from src.agent.liaison import liaison_agent

# Test intent classification
result = liaison_agent.process_message(
    user_message="What is the leave policy?",
    tenant_id="acme_corp",
    user_id="test_user"
)
```

## Project Structure

```
liaison-agent/
├── src/
│   ├── agent/
│   │   └── liaison.py          # Core agent logic
│   ├── api/
│   │   └── main.py             # FastAPI application
│   ├── config/
│   │   └── settings.py         # Configuration
│   ├── messaging/
│   │   └── redis_client.py     # Redis integration
│   └── schemas/
│       ├── liaison_message.py  # API schemas
│       └── mcp_message.py      # MCP protocol schemas
├── logs/                        # Log files
├── test_liaison.py             # Test suite
├── verify_liaison.py           # Setup verification
├── start_liaison.bat           # Start script
├── setup.bat                   # Setup script
├── verify_liaison.bat          # Verify script
├── requirements.txt            # Dependencies
├── .env.template               # Environment template
└── README.md                   # This file
```

## Dependencies

- **FastAPI**: REST API framework
- **Google Gemini 2.5**: LLM for intent classification
- **Redis**: Message transport (MCP protocol)
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server
- **Loguru**: Structured logging

## Integration with AgenticHR

### Message Flow

1. **User → Liaison**: User sends message via POST /message
2. **Liaison → Guide**: Policy queries routed to Guide Agent via Redis
3. **Liaison → Orchestrator**: Task requests delegated to Orchestrator via Redis
4. **Guide → Liaison**: Policy responses returned via POST /guide-response
5. **Orchestrator → Liaison**: Approval requests sent via POST /approval-request
6. **Liaison → User**: Formatted response returned

### Redis Streams

- **Publishes to**: `guide_agent:inbox`, `orchestrator_agent:inbox`
- **Subscribes to**: `liaison_agent:inbox`

## Conversation Management

The Liaison Agent maintains conversation context:

```python
# Multi-turn conversation example
# Turn 1
result1 = liaison_agent.process_message(
    "I want to apply for leave",
    tenant_id="acme_corp",
    user_id="emp123",
    workflow_id="WF_123"
)

# Turn 2 - remembers context
result2 = liaison_agent.process_message(
    "From March 15 to March 20",
    tenant_id="acme_corp",
    user_id="emp123",
    workflow_id="WF_123"  # Same workflow ID
)
```

## Troubleshooting

### Agent won't start
- Check `.env` file exists and has `GOOGLE_API_KEY`
- Verify conda environment activated: `conda env list`
- Check port 8002 not in use: `netstat -an | findstr 8002`

### Redis connection errors
- Start Redis server
- Check `REDIS_HOST` and `REDIS_PORT` in `.env`
- Test connection: `redis-cli ping`

### Import errors
- Run `setup.bat` to install dependencies
- Verify Python 3.10+: `python --version`

### Intent classification errors
- Verify Google API key is valid
- Check API quota: https://console.cloud.google.com
- Review logs in `logs/liaison.log`

## Development

### Adding New Intent Types

1. Add to `IntentType` enum in [src/agent/liaison.py](src/agent/liaison.py)
2. Update classification prompt
3. Add test case in [test_liaison.py](test_liaison.py)

### Adding New Actions

1. Add to `LiaisonAction` enum
2. Implement action handler
3. Update routing logic
4. Add API endpoint if needed

## License

Part of the AgenticHR system.

## Support

For issues or questions:
1. Check logs in `logs/liaison.log`
2. Run `verify_liaison.bat` to check setup
3. Review API docs: http://localhost:8002/docs
