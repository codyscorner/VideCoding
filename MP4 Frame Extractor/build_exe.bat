@echo off
echo Building MP4 Frame Extractor Executable...
echo.

pyinstaller --name="MP4FrameExtractor" ^
    --onefile ^
    --windowed ^
    --icon=app_icon.ico ^
    --add-data="ui/styles.py;ui" ^
    --add-data="config.py;." ^
    --hidden-import=cv2 ^
    --clean ^
    frame_extractor.py

echo.
echo Build complete! Check the 'dist' folder for MP4FrameExtractor.exe
pause
