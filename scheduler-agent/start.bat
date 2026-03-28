@echo off
REM Scheduler Agent Start Script
REM Uses conda environment: agenticHR

echo ================================================
echo   AgenticHR - Starting Scheduler Agent
echo ================================================

REM Check .env
if not exist .env (
    echo ERROR: .env file not found!
    echo Run setup.bat first.
    pause
    exit /b 1
)

REM Activate conda environment
echo Activating conda environment 'agenticHR'...
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate conda env 'agenticHR'
    pause
    exit /b 1
)
echo Conda environment 'agenticHR' activated.

REM Ensure logs directory exists
if not exist logs mkdir logs

echo.
echo Starting Scheduler Agent...
echo API will be available at: http://localhost:8004
echo API Docs: http://localhost:8004/docs
echo.
echo Press Ctrl+C to stop
echo.

python src/main.py
