@echo off
:: build.bat
:: Builds ComfyUI_Chain_Automator.exe with PyInstaller and deploys to
:: P:\Apps\VibeCoded\ComfyUI Chain Automator (skips deploy if the EXE there is in use)

cd /d "%~dp0"

echo === ComfyUI Chain Automator EXE Builder ===
echo Working directory: %CD%
echo.

python build_exe.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check output above.
    pause
    exit /b 1
)

echo.
pause
