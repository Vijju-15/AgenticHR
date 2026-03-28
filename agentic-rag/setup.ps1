# HR Assistant Agent - Setup and Run Guide

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HR Assistant Agent - Agentic RAG System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists and has API key
if (Test-Path .env) {
    $envContent = Get-Content .env -Raw
    if ($envContent -notmatch 'ANTHROPIC_API_KEY=.+') {
        Write-Host "⚠️  WARNING: ANTHROPIC_API_KEY not set in .env file" -ForegroundColor Yellow
        Write-Host "Please add your Anthropic API key to the .env file" -ForegroundColor Yellow
        Write-Host ""
        $apiKey = Read-Host "Enter your Anthropic API key (or press Enter to skip)"
        if ($apiKey) {
            (Get-Content .env) -replace 'ANTHROPIC_API_KEY=.*', "ANTHROPIC_API_KEY=$apiKey" | Set-Content .env
            Write-Host "✓ API key saved to .env" -ForegroundColor Green
        }
    }
} else {
    Write-Host "❌ .env file not found. Creating from .env.example..." -ForegroundColor Red
    Copy-Item .env.example .env
    Write-Host "Please edit .env and add your Anthropic API key" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Step 1: Checking dependencies..." -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Setting up virtual environment..." -ForegroundColor Cyan

# Create and activate virtual environment
if (!(Test-Path venv)) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "Step 3: Installing dependencies..." -ForegroundColor Cyan
Write-Host "This may take a few minutes..." -ForegroundColor Yellow

pip install --upgrade pip
pip install -r requirements.txt

Write-Host "✓ Dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Starting Qdrant vector database..." -ForegroundColor Cyan

# Check if Docker is running
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker is running" -ForegroundColor Green
        
        # Check if Qdrant is already running
        $qdrantRunning = docker ps --filter "name=qdrant" --format "{{.Names}}" 2>&1
        
        if ($qdrantRunning -eq "qdrant") {
            Write-Host "✓ Qdrant is already running" -ForegroundColor Green
        } else {
            Write-Host "Starting Qdrant container..." -ForegroundColor Yellow
            docker run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_data:/qdrant/storage qdrant/qdrant
            Start-Sleep -Seconds 5
            Write-Host "✓ Qdrant started" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "⚠️  Docker not running. You can start Qdrant later with:" -ForegroundColor Yellow
    Write-Host "   docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 5: Ingesting knowledge base..." -ForegroundColor Cyan

try {
    python -m src.rag.ingestion
    Write-Host "✓ Knowledge base ingested" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Knowledge base ingestion failed. Make sure Qdrant is running." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the API server, run:" -ForegroundColor Yellow
Write-Host "   python -m src.api.main" -ForegroundColor White
Write-Host ""
Write-Host "Or use uvicorn:" -ForegroundColor Yellow
Write-Host "   uvicorn src.api.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000" -ForegroundColor White
Write-Host "   http://localhost:8000/docs (API Documentation)" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
