@echo off
REM Run Liaison Agent tests - Optional batch file helper
REM You can also run directly: conda activate agenticHR && python test_liaison.py

echo ====================================
echo Running Liaison Agent Tests
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

REM Run tests
echo.
echo Running test suite...
echo.
python test_liaison.py

echo.
echo ====================================
echo Test run complete
echo ====================================
echo.
pause
