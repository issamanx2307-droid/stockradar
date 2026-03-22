@echo off
cd /d D:\stockradar
echo [1] Django check...
.venv\Scripts\python manage.py check 2>&1
echo.
echo [2] Migrate...
.venv\Scripts\python manage.py migrate 2>&1
echo.
echo [3] Python path test...
.venv\Scripts\python -c "import sys; sys.path.insert(0,'D:/stockradar'); from indicator_engine.indicators import compute_all; from scoring_engine.scoring import calculate_score; from decision_engine.decision import make_decision; print('Engine OK')" 2>&1
echo.
pause
