@echo off
REM Setup Liaison Agent - Optional batch file helper
REM You can also run directly: conda activate agenticHR && pip install -r requirements.txt

echo ====================================
echo Liaison Agent Setup
echo ====================================

REM Activate conda environment
echo Activating conda environment: agenticHR...
call conda activate agenticHR
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment 'agenticHR'
    echo.
    echo Please create the environment first:
    echo   conda create -n agenticHR python=3.10
    echo   conda activate agenticHR
    echo.
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ====================================
echo Setup completed successfully!
echo ====================================
echo.
echo Next steps:
echo 1. Create .env file: copy .env.template .env
echo 2. Edit .env and add your GOOGLE_API_KEY
echo 3. Verify setup: python verify_liaison.py
echo 4. Start agent: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
echo.
echo See CMD_QUICKSTART.md for direct CMD commands
echo.
pause
