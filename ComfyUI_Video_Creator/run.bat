@echo off
:: Run ComfyUI Video Creator from source (uses the repo .venv when present).
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" main.py
) else (
    python main.py
)
