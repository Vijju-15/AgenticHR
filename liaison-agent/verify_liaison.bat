@echo off
REM Verify Liaison Agent - Optional batch file helper
REM You can also run directly: conda activate agenticHR && python verify_liaison.py

echo ====================================
echo Verifying Liaison Agent Setup
echo ====================================

REM Activate conda environment
echo Activating conda environment: agenticHR...
call conda activate agenticHR
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment 'agenticHR'
    echo.
    echo Create it first: conda create -n agenticHR python=3.10
    echo.
    pause
    exit /b 1
)

REM Run verification script
echo.
echo Running verification checks...
echo.
python verify_liaison.py

echo.
pause
