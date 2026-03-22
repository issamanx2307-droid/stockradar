@echo off
title Radar หุ้น — Stop Server
color 0C

echo.
echo  ============================================
echo   🛑 Radar หุ้น — หยุดระบบทั้งหมด
echo  ============================================
echo.

echo  ⏹ หยุด Django (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  ⏹ หยุด Vite (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  ⏹ หยุด Python processes...
taskkill /IM python.exe /F >nul 2>&1

echo  ⏹ หยุด Node processes...
taskkill /IM node.exe /F >nul 2>&1

echo.
echo  ✅ หยุดระบบทั้งหมดแล้ว
echo.
pause
