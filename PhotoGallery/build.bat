@echo off
echo Building Photo Gallery...
pyinstaller PhotoGallery.spec --clean
if %errorlevel% == 0 (
    echo.
    echo Build successful! Output in dist\PhotoGallery\
) else (
    echo.
    echo Build failed.
)
pause
