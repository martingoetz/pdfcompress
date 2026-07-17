@echo off
git add .
set /p MSG="Commit-Beschreibung: "
git commit -m "%MSG%"
git push
