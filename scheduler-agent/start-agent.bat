@echo off
title SCHEDULER :8004
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
cd /d C:\AgenticHR\scheduler-agent
python -m uvicorn src.main:app --host 0.0.0.0 --port 8004
pause
