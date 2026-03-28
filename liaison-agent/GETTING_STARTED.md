# Getting Started - Liaison Agent

## Quickest Way to Run (CMD Prompt)

### 1. One-Time Setup

```cmd
cd C:\AgenticHR\liaison-agent
conda activate agenticHR
pip install -r requirements.txt
copy .env.template .env
```

Edit `.env` file and add your `GOOGLE_API_KEY`

### 2. Every Time You Start

```cmd
cd C:\AgenticHR\liaison-agent
conda activate agenticHR
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

That's it! Agent runs at http://localhost:8002

---

## Optional: Use Batch Files

Don't want to type commands? Use these instead:

```cmd
setup.bat          :: Install dependencies
verify_liaison.bat :: Check everything works
start_liaison.bat  :: Start the agent
test_liaison.bat   :: Run tests
```

---

## Where to Get Google API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste it in `.env` file: `GOOGLE_API_KEY=your_key_here`

---

## What Each File Does

- **src/agent/liaison.py** - Core agent with Gemini AI
- **src/api/main.py** - REST API (FastAPI)
- **requirements.txt** - Python packages needed
- **.env** - Your configuration (API keys, etc.)
- **verify_liaison.py** - Checks if setup is correct
- **test_liaison.py** - Tests the agent works

---

## Common Issues

**"conda: command not found"**
- Install Anaconda or Miniconda first

**"agenticHR environment not found"**
```cmd
conda create -n agenticHR python=3.10
conda activate agenticHR
```

**"Port 8002 already in use"**
- Change `API_PORT=8003` in `.env` file
- Or kill the process: `netstat -ano | findstr :8002`

**"Google API key not set"**
- Edit `.env` file and add: `GOOGLE_API_KEY=your_actual_key`

---

## Documentation

- **CMD_QUICKSTART.md** - All CMD commands
- **SETUP_GUIDE.md** - Detailed setup instructions  
- **README.md** - Complete documentation
- http://localhost:8002/docs - API documentation (when running)

---

## Testing It Works

After starting the agent, open another CMD window:

```cmd
curl http://localhost:8002/health
```

You should see: `{"status":"healthy","agent":"liaison_agent","version":"1.0.0"}`

Or open in browser: http://localhost:8002/docs
