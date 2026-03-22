@echo off
title StockRadar — ติดตั้ง Dependencies
color 0A
cd /d D:\stockradar

echo.
echo  ============================================
echo   📦 ติดตั้ง Dependencies ทั้งหมด
echo   (ข้ามการ build pandas/numpy ที่มีอยู่แล้ว)
echo  ============================================
echo.

echo  [1/6] Django + REST Framework...
.venv\Scripts\pip install "Django==5.0.0" djangorestframework djangorestframework-simplejwt --no-deps

echo  [2/6] Auth + CORS...
.venv\Scripts\pip install django-cors-headers django-allauth dj-rest-auth

echo  [3/6] WebSocket (Channels + Daphne + Twisted)...
.venv\Scripts\pip install channels channels-redis daphne twisted autobahn

echo  [4/6] Admin UI + Utilities...
.venv\Scripts\pip install django-jazzmin python-dotenv lxml

echo  [5/6] Celery + Redis...
.venv\Scripts\pip install celery redis

echo  [6/6] yfinance + requests...
.venv\Scripts\pip install yfinance requests python-dateutil

echo.
echo  🔍 ตรวจสอบ import...
.venv\Scripts\python -c "import django, rest_framework, channels, daphne, twisted, jazzmin, lxml, celery, redis, yfinance; print('✅ ทุก package พร้อมใช้งาน!')"

echo.
pause
