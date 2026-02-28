@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: build_exe.bat  —  Build PictureFlipper.exe with PyInstaller
::
:: Run from the Picture_Fipper\ directory (or double-click).
:: Output: dist\PictureFlipper\PictureFlipper.exe  + _internal\ folder
:: ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

echo [1/4] Installing / verifying dependencies...
pip install pyinstaller pillow pyside6 ultralytics deepface tf-keras numpy --quiet

echo [2/4] Running PyInstaller...
pyinstaller PictureFlipper.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    pause
    exit /b 1
)

echo [3/4] Copying models directory to dist...
if exist "models\yolov8n.pt" (
    xcopy /Y /I "models\yolov8n.pt" "dist\PictureFlipper\models\" >nul
    echo   models\yolov8n.pt copied.
) else (
    echo   WARNING: models\yolov8n.pt not found — copy it manually to dist\PictureFlipper\models\
)

echo [4/4] Copying DeepFace weights (Facenet)...
set WEIGHTS_SRC=%USERPROFILE%\.deepface\weights
set WEIGHTS_DST=dist\PictureFlipper\.deepface\weights
if exist "%WEIGHTS_SRC%\facenet_weights.h5" (
    xcopy /Y /I "%WEIGHTS_SRC%\facenet_weights.h5" "%WEIGHTS_DST%\" >nul
    echo   facenet_weights.h5 copied to dist\PictureFlipper\.deepface\weights\
) else (
    echo   WARNING: facenet_weights.h5 not found at %WEIGHTS_SRC%
    echo   Run the app once in dev mode to download it, or copy manually.
)
:: Copy any other deepface weights that exist (opencv haarcascades etc.)
if exist "%WEIGHTS_SRC%\opencv_face_detector.caffemodel" (
    xcopy /Y /I "%WEIGHTS_SRC%\opencv_face_detector.caffemodel" "%WEIGHTS_DST%\" >nul
)
if exist "%WEIGHTS_SRC%\opencv_face_detector_uint8.pb" (
    xcopy /Y /I "%WEIGHTS_SRC%\opencv_face_detector_uint8.pb" "%WEIGHTS_DST%\" >nul
)

echo.
echo Build complete!
echo Output: dist\PictureFlipper\PictureFlipper.exe
echo.
pause
