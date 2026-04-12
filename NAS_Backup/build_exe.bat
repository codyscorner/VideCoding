@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: build_exe.bat  —  Build NAS_Backup.exe with PyInstaller
::
:: Run from the NAS_Backup\ directory (or double-click).
:: Output: dist\NAS_Backup.exe  (single-file, no console)
:: ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

echo [1/3] Installing / verifying dependencies...
call venv\Scripts\activate.bat
pip install pyinstaller --quiet

echo [2/3] Running PyInstaller...
pyinstaller NAS_Backup.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo Output: dist\NAS_Backup.exe
echo.
echo To run headless (Task Scheduler):
echo   NAS_Backup.exe --run
echo.
pause
