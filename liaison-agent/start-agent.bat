@echo off
title LIAISON :8002
call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR
cd /d C:\AgenticHR\liaison-agent
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002
pause
