@echo off
REM Launch Music Player from this folder, regardless of where run.bat is called.
cd /d "%~dp0"

REM Prefer the project venv (has tinytag etc.); fall back to PATH python.
set "VENV_PY=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" main.py %*
) else (
    python main.py %*
)
if errorlevel 1 pause
