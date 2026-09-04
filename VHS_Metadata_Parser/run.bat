@echo off
REM Run VHS Metadata Parser from source, from wherever run.bat is called.
REM Optional: pass a metadata file path to open it on launch, e.g.  run.bat Test_files\MiniMax_H3_00008-audio.mp4
cd /d "%~dp0"

REM Prefer the shared VideCoding venv; fall back to python on PATH.
set "VENV_PY=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" vhs_metadata_parser.py %*
) else (
    python vhs_metadata_parser.py %*
)
if errorlevel 1 pause
