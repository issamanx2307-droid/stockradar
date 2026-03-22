@echo off
setlocal
title Radar Stock System
color 0A
cd /d D:\stockradar

echo.
echo  ============================================================
echo   Radar - Stock Analysis System
echo  ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  ERROR: .venv not found. Run install_deps.bat first.
    pause
    exit /b 1
)

if not exist "manage.py" (
    echo  ERROR: manage.py not found in D:\stockradar
    pause
    exit /b 1
)

if not exist "logs" mkdir logs

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set DJANGO_SETTINGS_MODULE=stockradar.settings

echo  Running setup check...
echo  (First run may take 1-2 hours to load 5 years of data)
echo.

.venv\Scripts\python -W ignore setup_check.py
echo.

if not exist "staticfiles\jazzmin" (
    echo  Collecting static files...
    .venv\Scripts\python -W ignore manage.py collectstatic --noinput 1>nul 2>nul
    echo  Done.
    echo.
)

echo  Starting Daphne ASGI (port 8000)...
start "Daphne" cmd /k "set PYTHONIOENCODING=utf-8 && cd /d D:\stockradar && .venv\Scripts\python -W ignore -m daphne -b 0.0.0.0 -p 8000 stockradar.asgi:application"
timeout /t 3 /nobreak 1>nul

echo  Starting Scheduler...
start "Scheduler" cmd /k "set PYTHONIOENCODING=utf-8 && cd /d D:\stockradar && .venv\Scripts\python -W ignore manage.py start_scheduler"
timeout /t 2 /nobreak 1>nul

echo  Starting Vite (port 5173)...
start "Vite" cmd /k "cd /d D:\stockradar\frontend && npm run dev"
timeout /t 5 /nobreak 1>nul

start "" "http://localhost:5173"

echo.
echo  ============================================================
echo   System is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   Admin    : http://localhost:8000/admin/
echo  ============================================================
echo.
pause
