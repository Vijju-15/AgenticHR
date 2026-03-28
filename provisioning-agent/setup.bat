@echo off
REM Provisioning Agent Setup Script for Command Prompt
REM Run this to set up the agent environment

echo ========================================
echo   Provisioning Agent Setup
echo ========================================

REM Check Python version
echo.
echo [1/5] Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.9 or higher.
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Skipping...
) else (
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [4/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Dependencies installed successfully

REM Create .env file from example
echo.
echo [5/5] Setting up environment file...
if exist .env (
    echo .env file already exists. Skipping...
) else (
    copy .env.example .env
    echo Created .env file from template
    echo WARNING: Please update .env with your configuration!
)

REM Create logs directory
if not exist logs (
    mkdir logs
    echo Created logs directory
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update .env file with your configuration
echo    Run: notepad .env
echo.
echo 2. Ensure Redis is running (localhost:6379)
echo    Check: docker ps
echo.
echo 3. Start the agent
echo    Run: start.bat
echo.
pause
