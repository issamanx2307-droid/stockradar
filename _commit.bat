@echo off
cd /d D:\stockradar
git add -A
git commit -m "fix: free tier render.yaml, merge scheduler into web process"
git push
echo Done.
