# Start Liaison Agent
# PowerShell script to run the Liaison Agent

Write-Host "Starting Liaison Agent..." -ForegroundColor Cyan

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please create a .env file with required configuration." -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
try {
    $pythonVersion = python --version
    Write-Host "Python detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python not found!" -ForegroundColor Red
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "Created logs directory" -ForegroundColor Green
}

# Start the Liaison Agent
Write-Host "`nStarting Liaison Agent on port 8002..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

try {
    python -m uvicorn src.api.liaison_main:app --host 0.0.0.0 --port 8002 --reload
} catch {
    Write-Host "`nLiaison Agent stopped" -ForegroundColor Yellow
}
