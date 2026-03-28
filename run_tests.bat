@echo off
REM AgenticHR – Full Backend Test Suite launcher

call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate agenticHR

cd /d C:\AgenticHR
python -W ignore test_full_backend.py %*

pause
