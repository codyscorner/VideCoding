@echo off
:: Automatically request administrator privileges
:: Check for permissions
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    goto :run
) else (
    echo Requesting administrator privileges...
    goto :elevate
)

:elevate
:: Use PowerShell to re-run this batch file as administrator
powershell -Command "Start-Process '%~f0' -Verb RunAs"
exit /b

:run
:: Run the backup script
echo Starting NAS Backup Script...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0NAS_Backup.ps1"
pause
