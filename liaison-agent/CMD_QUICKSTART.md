# Liaison Agent - CMD Quick Reference

## Running in CMD with agenticHR Conda Environment

All commands assume you're running in CMD prompt with the agenticHR conda environment activated.

### Initial Setup (One Time)

```cmd
:: Navigate to liaison-agent folder
cd C:\AgenticHR\liaison-agent

:: Activate conda environment
conda activate agenticHR

:: Install dependencies
pip install -r requirements.txt

:: Create environment file
copy .env.template .env

:: Edit .env file and add your GOOGLE_API_KEY
notepad .env
```

### Daily Usage

```cmd
:: Navigate to folder
cd C:\AgenticHR\liaison-agent

:: Activate conda environment
conda activate agenticHR

:: Start the agent
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

### Common Commands

#### Verify Setup
```cmd
conda activate agenticHR
python verify_liaison.py
```

#### Run Tests
```cmd
conda activate agenticHR
python test_liaison.py
```

#### Start Agent (Development Mode)
```cmd
conda activate agenticHR
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

#### Start Agent (Production Mode)
```cmd
conda activate agenticHR
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --workers 4
```

#### Check Agent Status
Open browser: http://localhost:8002/health

#### View API Documentation
Open browser: http://localhost:8002/docs

#### Install/Update Dependencies
```cmd
conda activate agenticHR
pip install -r requirements.txt --upgrade
```

#### Clear Logs
```cmd
del logs\*.log
```

### Troubleshooting

#### Conda environment not found
```cmd
:: Check available environments
conda env list

:: Create agenticHR environment if missing
conda create -n agenticHR python=3.10

:: Activate it
conda activate agenticHR
```

#### Module import errors
```cmd
:: Make sure you're in the right directory
cd C:\AgenticHR\liaison-agent

:: Reinstall dependencies
conda activate agenticHR
pip install -r requirements.txt
```

#### Port already in use
```cmd
:: Check what's using port 8002
netstat -ano | findstr :8002

:: Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

:: Or change the port in .env file
notepad .env
:: Set API_PORT=8003 or another available port
```

#### Redis connection errors
```cmd
:: Check if Redis is running (if installed)
redis-cli ping

:: Update Redis settings in .env if needed
notepad .env
```

### Environment Variables (.env)

Required settings in `.env` file:

```env
# Required - Get from Google AI Studio
GOOGLE_API_KEY=your_google_api_key_here

# Redis Settings (required for production, optional for testing)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API Settings
API_HOST=0.0.0.0
API_PORT=8002
API_WORKERS=1

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Quick Test

After starting the agent, test it with curl or PowerShell:

```powershell
# Using PowerShell to test the API
Invoke-RestMethod -Uri "http://localhost:8002/health" -Method GET

# Test a message (replace with actual values)
$body = @{
    message = "What is the leave policy?"
    user_id = "test_user"
    tenant_id = "acme_corp"
    user_name = "Test User"
    user_role = "employee"
    metadata = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8002/message" -Method POST -Body $body -ContentType "application/json"
```

### File Structure Reference

```
C:\AgenticHR\liaison-agent\
├── src\                    # Source code
│   ├── agent\             # Core agent logic
│   ├── api\               # FastAPI endpoints
│   ├── config\            # Configuration
│   ├── messaging\         # Redis messaging
│   └── schemas\           # Data models
├── logs\                   # Log files (auto-created)
├── test_liaison.py         # Test suite
├── verify_liaison.py       # Verification script
├── requirements.txt        # Dependencies
├── .env                    # Your environment config (create from .env.template)
├── .env.template          # Environment template
└── README.md              # Full documentation
```

### Batch Files (Optional)

If you prefer not typing the full commands, use these batch files:

- `setup.bat` - Install dependencies
- `verify_liaison.bat` - Verify setup
- `start_liaison.bat` - Start agent
- `test_liaison.bat` - Run tests

All batch files automatically activate the agenticHR conda environment.

### Integration with Other Agents

The Liaison Agent communicates with other agents via Redis:

- **Port**: 8002 (Liaison Agent)
- **Port**: 8001 (Orchestrator Agent) 
- **Redis**: localhost:6379 (default)

Make sure Redis is running for inter-agent communication:
```cmd
:: If you have Redis installed locally
redis-server

:: Check Redis status
redis-cli ping
```

### Getting Help

- Full docs: `README.md`
- Setup guide: `SETUP_GUIDE.md`
- API docs: http://localhost:8002/docs (when running)
- Logs: `logs\liaison.log`
