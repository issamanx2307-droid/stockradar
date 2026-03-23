@echo off
cd /d D:\stockradar
git add -A
git commit -m "fix: watchlist 500 error - remove duplicate session-based views, add missing calc-sell/alert/history/fundamental views"
git push
echo Done.
