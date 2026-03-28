@echo off
REM ============================================================
REM  AgenticHR — Start All Agents (CMD + Conda)
REM  Run this from: C:\AgenticHR
REM ============================================================

echo.
echo  AgenticHR — Starting All Agents
echo  ================================
echo.

REM Orchestrator  :8001
start "ORCHESTRATOR-8001" cmd /k "call C:\ProgramData\Anaconda3\Scripts\activate.bat && conda activate agenticHR && cd /d C:\AgenticHR\orchestrator-agent && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001"

timeout /t 2 /nobreak >nul

REM Liaison       :8002
start "LIAISON-8002" cmd /k "call C:\ProgramData\Anaconda3\Scripts\activate.bat && conda activate agenticHR && cd /d C:\AgenticHR\liaison-agent && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002"

timeout /t 2 /nobreak >nul

REM Provisioning  :8003
start "PROVISIONING-8003" cmd /k "call C:\ProgramData\Anaconda3\Scripts\activate.bat && conda activate agenticHR && cd /d C:\AgenticHR\provisioning-agent && python -m uvicorn src.main:app --host 0.0.0.0 --port 8003"

timeout /t 2 /nobreak >nul

REM Scheduler     :8004
start "SCHEDULER-8004" cmd /k "call C:\ProgramData\Anaconda3\Scripts\activate.bat && conda activate agenticHR && cd /d C:\AgenticHR\scheduler-agent && python -m uvicorn src.main:app --host 0.0.0.0 --port 8004"

timeout /t 3 /nobreak >nul

echo.
echo  All 4 agent windows launched!
echo.
echo  Ports:
echo    Orchestrator  → http://localhost:8001/health
echo    Liaison       → http://localhost:8002/health
echo    Provisioning  → http://localhost:8003/api/v1/health
echo    Scheduler     → http://localhost:8004/api/v1/health
echo.
pause
