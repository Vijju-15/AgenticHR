# Start Script for Orchestrator Agent (Conda Environment)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Orchestrator Agent - Quick Start" -ForegroundColor Cyan
Write-Host "   (Using Conda Environment)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (!(Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Edit .env file and add your GOOGLE_API_KEY" -ForegroundColor Red
    Write-Host "Get it from: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Press Enter to open .env file for editing, or Ctrl+C to exit"
    notepad .env
}

# Check for GOOGLE_API_KEY
$envContent = Get-Content ".env" -Raw
if ($envContent -match "GOOGLE_API_KEY=your-gemini-api-key-here" -or $envContent -notmatch "GOOGLE_API_KEY=AIza") {
    Write-Host "WARNING: GOOGLE_API_KEY not configured!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Get your API key from: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
    Write-Host "Then update it in .env file" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host "Checking dependencies..." -ForegroundColor Yellow
Write-Host ""

# Check if running in conda environment
$condaEnv = $env:CONDA_DEFAULT_ENV
if ($condaEnv) {
    Write-Host "Using conda environment: $condaEnv" -ForegroundColor Green
} else {
    Write-Host "WARNING: Not in a conda environment" -ForegroundColor Yellow
    Write-Host "Activate with: conda activate agenticHR" -ForegroundColor Yellow
    Write-Host ""
}

# Install dependencies if needed
Write-Host "Installing/updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "ERROR installing dependencies" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create logs directory
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Orchestrator Agent" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service will be available at:" -ForegroundColor Yellow
Write-Host "  http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor Yellow
Write-Host "  http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "NOTE:" -ForegroundColor Yellow
Write-Host "  - Redis should be running on localhost:6379" -ForegroundColor White
Write-Host "  - PostgreSQL should be running on localhost:5432" -ForegroundColor White
Write-Host "  - Configure these in .env file" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the service
python -m uvicorn src.main:app --reload --port 8001
