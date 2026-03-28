@echo off
REM Start Liaison Agent - Optional batch file helper
REM You can also run directly: conda activate agenticHR && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload

echo ====================================
echo Starting Liaison Agent
echo ====================================

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Create from template: copy .env.template .env
    echo Then edit it and add your GOOGLE_API_KEY
    echo.
    pause
    exit /b 1
)

REM Activate conda environment
echo Activating conda environment: agenticHR...
call conda activate agenticHR
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment 'agenticHR'
    echo.
    echo Check available environments: conda env list
    echo Create if needed: conda create -n agenticHR python=3.10
    echo.
    pause
    exit /b 1
)

REM Start the Liaison Agent
echo.
echo Starting Liaison Agent on port 8002...
echo API Docs will be at: http://localhost:8002/docs
echo.
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload

REM If we get here, the server stopped
echo.
echo Liaison Agent stopped.
pause
