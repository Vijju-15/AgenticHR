@echo off
REM Test Provisioning Agent

echo ========================================
echo   Testing Provisioning Agent
echo ========================================

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run setup.ps1 first
    exit /b 1
)

echo.
echo Running tests...
echo.

python test_provisioning.py

echo.
echo Done!
pause
