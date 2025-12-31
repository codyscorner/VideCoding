@echo off
echo Creating Python virtual environment...

REM Create virtual environment
python -m venv venv

if errorlevel 1 (
    echo Failed to create virtual environment.
    echo Make sure Python is installed and added to PATH.
    pause
    exit /b 1
)

echo Virtual environment created successfully!
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate
echo.
echo To deactivate when done, run:
echo   deactivate
echo.
pause
