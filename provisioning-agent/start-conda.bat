@echo off
REM Start Provisioning Agent using conda environment
REM Make sure your conda environment is activated first!

echo ========================================
echo   Starting Provisioning Agent (Conda)
echo ========================================

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please run setup-conda.bat first
    pause
    exit /b 1
)

REM Check if conda environment is activated
echo.
echo Make sure your conda environment (agenticHR) is activated!
echo If not, run: conda activate agenticHR
echo.

REM Check Redis connection
echo Checking Redis connection...
docker exec -it agentichr-redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo Redis is running
) else (
    echo WARNING: Could not verify Redis connection
    echo Make sure Redis is running on localhost:6379
)

echo.
echo ========================================
echo Starting Provisioning Agent...
echo ========================================
echo.
echo API will be available at: http://localhost:8003
echo API Docs: http://localhost:8003/docs
echo.
echo Press Ctrl+C to stop
echo.

REM Start the agent
python -m src.main
