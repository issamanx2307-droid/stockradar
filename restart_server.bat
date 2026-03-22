@echo off
title Kill Port 8000
cd /d D:\stockradar

echo Stopping port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
    echo Killed PID %%a
)
timeout /t 2 /nobreak >nul

echo Starting Daphne...
.venv\Scripts\python -W ignore -m daphne -b 0.0.0.0 -p 8000 stockradar.asgi:application
