@echo off
:: Python NAS Backup Script Launcher
echo ========================================
echo Starting NAS Backup Script (Python)
echo ========================================
echo.

:: Run the Python backup script
python "%~dp0nas_backup.py"

:: Batch file will wait for Python script to finish
:: Python script has its own "Press Enter to exit" prompt
