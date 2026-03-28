# Start Provisioning Agent
# This script starts the Provisioning Agent

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Provisioning Agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Check Redis connection
Write-Host "`nChecking Redis connection..." -ForegroundColor Yellow
try {
    $redisCheck = docker exec -it agentichr-redis redis-cli ping 2>&1
    if ($redisCheck -match "PONG") {
        Write-Host "✅ Redis is running" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Could not verify Redis connection" -ForegroundColor Yellow
        Write-Host "Make sure Redis is running on localhost:6379" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check Redis (is Docker running?)" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🚀 Starting Provisioning Agent..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API will be available at: http://localhost:8003" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8003/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the agent
python -m src.main
