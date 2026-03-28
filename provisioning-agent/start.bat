@echo off
REM Batch script to start Provisioning Agent

echo ========================================
echo   Starting Provisioning Agent
echo ========================================

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please run setup.ps1 first
    exit /b 1
)

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run setup.ps1 first
    exit /b 1
)

echo.
echo Starting Provisioning Agent...
echo API will be available at: http://localhost:8003
echo API Docs: http://localhost:8003/docs
echo.
echo Press Ctrl+C to stop
echo.

REM Start the agent
python -m src.main
