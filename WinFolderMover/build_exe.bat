@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: build_exe.bat  —  Build WinFolderMover.exe with PyInstaller
::
:: Run from the WinFolderMover\ directory (or double-click).
:: Output: dist\WinFolderMover.exe  (single-file, no console)
:: ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

echo [1/3] Installing / verifying dependencies...
call venv\Scripts\activate.bat
pip install pyinstaller --quiet

echo [2/3] Running PyInstaller...
pyinstaller WinFolderMover.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo Output: dist\WinFolderMover.exe
echo.
pause
