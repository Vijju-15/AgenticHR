@echo off
title ORCHESTRATOR :8001
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
cd /d C:\AgenticHR\orchestrator-agent
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
pause
