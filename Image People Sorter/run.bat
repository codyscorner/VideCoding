@echo off
cd /d "%~dp0"
"C:\Users\cody\AppData\Local\Programs\Python\Python312\python.exe" main.py
if errorlevel 1 (
    echo.
    echo App exited with an error. Press any key to close.
    pause >nul
)
