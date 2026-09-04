@echo off
cd /d "%~dp0"
:: The repo .venv has every dependency (incl. boto3 for the LoRA pod check);
:: the system Python does not.
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" main.py
) else (
    python main.py
)
pause
