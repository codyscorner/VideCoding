@echo off
echo ============================================
echo  Folder Backup Archiver - Build EXE
echo ============================================
echo.

pyinstaller ^
  --onefile ^
  --noconsole ^
  --name "FolderBackupArchiver" ^
  --add-data "utils;utils" ^
  backup_tool.py

echo.
if exist "dist\FolderBackupArchiver.exe" (
    echo Build successful: dist\FolderBackupArchiver.exe
    echo.
    echo IMPORTANT: Copy the following folder next to the EXE:
    echo   7z2601-extra\
) else (
    echo Build FAILED. Check output above.
)
echo.
pause
