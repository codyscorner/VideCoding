@echo off
rem Run PDF Edit from source (uses the VideCoding venv)
cd /d "%~dp0"
"P:\AI\VideCoding\.venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
