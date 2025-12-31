@echo off
echo Building Frame Extractor Executable...
echo.

pyinstaller --name="FrameExtractor" ^
    --onefile ^
    --windowed ^
    --icon=NONE ^
    --add-data="frame_extractor.py;." ^
    --hidden-import=cv2 ^
    --hidden-import=tkinter ^
    --clean ^
    frame_extractor.py

echo.
echo Build complete! Check the 'dist' folder for FrameExtractor.exe
pause
