@echo off
REM Setup Provisioning Agent using existing conda environment
REM Use this if you already have a conda environment

echo ========================================
echo   Provisioning Agent Setup (Conda)
echo ========================================

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Conda not found in PATH
    echo Please ensure Anaconda/Miniconda is installed and conda is in PATH
    pause
    exit /b 1
)

echo.
echo Using existing conda environment...
echo Make sure your conda environment is activated before running this.
echo.
echo [1/3] Installing dependencies into current environment...

REM Install dependencies
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Dependencies installed successfully

REM Create .env file from example
echo.
echo [2/3] Setting up environment file...
if exist .env (
    echo .env file already exists. Skipping...
) else (
    copy .env.example .env
    echo Created .env file from template
    echo WARNING: Please update .env with your configuration!
)

REM Create logs directory
echo.
echo [3/3] Creating logs directory...
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
echo 3. Start the agent with your conda env activated
echo    Run: start-conda.bat
echo.
pause
