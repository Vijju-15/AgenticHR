# Quick Start Script for Orchestrator Agent

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Orchestrator Agent - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (!(Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run setup first:" -ForegroundColor Yellow
    Write-Host "  .\setup.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Then configure your Gemini API key in .env" -ForegroundColor Yellow
    exit 1
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

Write-Host "Starting required services..." -ForegroundColor Yellow
Write-Host ""

# Start Redis
Write-Host "Starting Redis..." -ForegroundColor Yellow
$redisRunning = docker ps --filter "name=agentichr-redis" --format "{{.Names}}"
if ($redisRunning) {
    Write-Host "Redis already running" -ForegroundColor Green
} else {
    docker run -d --name agentichr-redis -p 6379:6379 redis:7-alpine | Out-Null
    Start-Sleep -Seconds 2
    Write-Host "Redis started" -ForegroundColor Green
}

# Start PostgreSQL
Write-Host "Starting PostgreSQL..." -ForegroundColor Yellow
$pgRunning = docker ps --filter "name=agentichr-postgres" --format "{{.Names}}"
if ($pgRunning) {
    Write-Host "PostgreSQL already running" -ForegroundColor Green
} else {
    # Extract password from .env
    $pgPassword = (Get-Content ".env" | Select-String "POSTGRES_PASSWORD=").ToString().Split("=")[1]
    if (!$pgPassword -or $pgPassword -eq "your-password-here") {
        $pgPassword = "agentichr_dev_pass"
        Write-Host "Using default PostgreSQL password" -ForegroundColor Yellow
    }
    
    docker run -d `
        --name agentichr-postgres `
        -e POSTGRES_DB=agentichr `
        -e POSTGRES_USER=postgres `
        -e "POSTGRES_PASSWORD=$pgPassword" `
        -p 5432:5432 `
        postgres:15-alpine | Out-Null
    
    Start-Sleep -Seconds 3
    Write-Host "PostgreSQL started" -ForegroundColor Green
}

Write-Host ""
Write-Host "Services ready!" -ForegroundColor Green
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found. Run setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
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
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the service
python -m uvicorn src.main:app --reload --port 8001
