@echo off
echo ================================================
echo   AgenticHR  Frontend  (Next.js)
echo ================================================

cd /d "%~dp0"

IF NOT EXIST "node_modules" (
    echo [1/2] Installing dependencies...
    call npm install
)

echo [2/2] Starting dev server on http://localhost:3000
call npm run dev
