@echo off
REM Start Script for Orchestrator Agent (Conda - CMD)

echo.
echo ========================================
echo    Orchestrator Agent - Quick Start
echo    (Using Conda Environment)
echo ========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Creating .env from template...
    copy .env.example .env
    echo .env file created
    echo.
    echo IMPORTANT: Edit .env file and add your GOOGLE_API_KEY
    echo Get it from: https://aistudio.google.com/app/apikey
    echo.
    pause
    notepad .env
)

REM Check conda environment
if "%CONDA_DEFAULT_ENV%"=="" (
    echo WARNING: Not in a conda environment
    echo Please activate with: conda activate agenticHR
    echo.
    pause
    exit /b 1
)

echo Using conda environment: %CONDA_DEFAULT_ENV%
echo.

echo Installing/updating dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR installing dependencies
    pause
    exit /b 1
)
echo Dependencies installed
echo.

REM Create logs directory
if not exist "logs" mkdir logs

echo ========================================
echo    Starting Orchestrator Agent
echo ========================================
echo.
echo Service will be available at:
echo   http://localhost:8001
echo.
echo API Documentation:
echo   http://localhost:8001/docs
echo.
echo NOTE:
echo   - Redis should be running on localhost:6379
echo   - PostgreSQL should be running on localhost:5432
echo   - Configure these in .env file
echo.
echo Press Ctrl+C to stop
echo.

REM Start the service
python -m uvicorn src.main:app --reload --port 8001
