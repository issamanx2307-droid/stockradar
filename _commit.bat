@echo off
cd /d D:\stockradar
git add -A
git commit -m "feat: merge Signals into Dashboard, remove PositionAnalysis, fix TickerTape animation"
git push
echo Done.
