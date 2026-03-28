# Stop Script for Orchestrator Agent

Write-Host ""
Write-Host "Stopping Orchestrator Agent services..." -ForegroundColor Yellow
Write-Host ""

# Stop Docker containers
Write-Host "Stopping Redis..." -ForegroundColor Yellow
docker stop agentichr-redis 2>$null
docker rm agentichr-redis 2>$null
Write-Host "Redis stopped" -ForegroundColor Green

Write-Host "Stopping PostgreSQL..." -ForegroundColor Yellow
docker stop agentichr-postgres 2>$null
docker rm agentichr-postgres 2>$null
Write-Host "PostgreSQL stopped" -ForegroundColor Green

Write-Host ""
Write-Host "All services stopped!" -ForegroundColor Green
Write-Host ""
