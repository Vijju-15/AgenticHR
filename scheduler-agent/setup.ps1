# Scheduler Agent Setup Script (PowerShell)
# Installs dependencies into the shared conda environment: agenticHR

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  AgenticHR – Scheduler Agent Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# --- Activate conda base then agenticHR env ---
Write-Host "Activating conda environment 'agenticHR' ..." -ForegroundColor Yellow
& "C:/ProgramData/Anaconda3/Scripts/activate"
conda activate agenticHR
Write-Host "✅ Conda environment 'agenticHR' activated" -ForegroundColor Green

# --- Install dependencies ---
Write-Host "Installing dependencies into conda env 'agenticHR' ..." -ForegroundColor Yellow
pip install --upgrade pip -q
pip install -r requirements.txt -q
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# --- Copy .env if missing ---
if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "⚠️  Copied .env.example → .env  (edit values before starting)" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env already exists" -ForegroundColor Green
}

# --- Ensure logs directory exists ---
New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null
Write-Host "✅ Logs directory ready" -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Setup complete!  Start agent with: .\start.ps1" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
