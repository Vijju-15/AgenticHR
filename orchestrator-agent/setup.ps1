# Orchestrator Agent Setup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AgenticHR - Orchestrator Agent Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green
Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "pip upgraded" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "Dependencies installed" -ForegroundColor Green
Write-Host ""

# Check for .env file
Write-Host "Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host ".env file exists" -ForegroundColor Green
} else {
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Edit .env file with your credentials!" -ForegroundColor Red
    Write-Host "   - Add your GOOGLE_API_KEY" -ForegroundColor Yellow
    Write-Host "   - Set POSTGRES_PASSWORD" -ForegroundColor Yellow
    Write-Host "   - Update DATABASE_URL" -ForegroundColor Yellow
}
Write-Host ""

# Create logs directory
Write-Host "Creating logs directory..." -ForegroundColor Yellow
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "Logs directory created" -ForegroundColor Green
} else {
    Write-Host "Logs directory exists" -ForegroundColor Green
}
Write-Host ""

# Check Redis
Write-Host "Checking Redis connection..." -ForegroundColor Yellow
try {
    $redisCheck = Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($redisCheck) {
        Write-Host "Redis is running on port 6379" -ForegroundColor Green
    } else {
        Write-Host "Redis not detected on port 6379" -ForegroundColor Yellow
        Write-Host "   Start Redis with: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check Redis connection" -ForegroundColor Yellow
}
Write-Host ""

# Check PostgreSQL
Write-Host "Checking PostgreSQL connection..." -ForegroundColor Yellow
try {
    $pgCheck = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($pgCheck) {
        Write-Host "PostgreSQL is running on port 5432" -ForegroundColor Green
    } else {
        Write-Host "PostgreSQL not detected on port 5432" -ForegroundColor Yellow
        Write-Host "   Install PostgreSQL from: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check PostgreSQL connection" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "          Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Get Gemini API Key: https://aistudio.google.com/app/apikey" -ForegroundColor White
Write-Host "2. Edit .env file with your credentials" -ForegroundColor White
Write-Host "3. Ensure Redis is running" -ForegroundColor White
Write-Host "4. Ensure PostgreSQL is running" -ForegroundColor White
Write-Host "5. Run: python -m uvicorn src.main:app --reload --port 8001" -ForegroundColor White
Write-Host ""
Write-Host "Documentation: README.md" -ForegroundColor Cyan
Write-Host ""
