# Scheduler Agent Start Script (PowerShell)
# Uses shared conda environment: agenticHR

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  AgenticHR – Starting Scheduler Agent" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Activate conda base then agenticHR env
Write-Host "Activating conda environment 'agenticHR' …" -ForegroundColor Yellow
& "C:/ProgramData/Anaconda3/Scripts/activate"
conda activate agenticHR
Write-Host "✅ Conda environment 'agenticHR' activated" -ForegroundColor Green

# Ensure logs directory exists
New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null

# Start the agent
Write-Host "Starting Scheduler Agent on port 8004 …" -ForegroundColor Yellow
python src/main.py
