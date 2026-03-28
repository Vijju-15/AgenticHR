@echo off
title PROVISIONING :8003
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
cd /d C:\AgenticHR\provisioning-agent
python -m uvicorn src.main:app --host 0.0.0.0 --port 8003
pause
