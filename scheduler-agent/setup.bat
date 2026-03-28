@echo off
REM Scheduler Agent Setup Script
REM Installs dependencies into conda environment: agenticHR

echo ================================================
echo   AgenticHR - Scheduler Agent Setup
echo ================================================

REM Activate conda base
echo.
echo [1/3] Activating conda environment 'agenticHR'...
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate conda env 'agenticHR'
    echo Make sure Anaconda is installed and the 'agenticHR' env exists.
    pause
    exit /b 1
)
echo Conda environment 'agenticHR' activated.

REM Install dependencies
echo.
echo [2/3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.

REM Copy .env if missing
echo.
echo [3/3] Checking .env file...
if not exist .env (
    copy .env.example .env
    echo Copied .env.example to .env - edit values before starting.
) else (
    echo .env already exists.
)

REM Ensure logs directory exists
if not exist logs mkdir logs
echo Logs directory ready.

echo.
echo ================================================
echo   Setup complete! Start with: start.bat
echo ================================================
pause
