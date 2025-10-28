ICON EMBEDDING ISSUE WITH PYINSTALLER
======================================

The application has been built with version 1.2.4 and PyInstaller reports
"Copying icon to EXE" but Windows Explorer doesn't show the icon.

This is a known PyInstaller issue on some Windows systems.

WORKAROUNDS:
------------

Option 1: Use Resource Hacker (GUI Tool - Recommended)
   1. Download Resource Hacker: http://www.angusj.com/resourcehacker/
   2. Open "File Rename Mover.exe" in Resource Hacker
   3. Action -> Replace Icon
   4. Select "app_icon.ico"
   5. Save

Option 2: Use rcedit (Command Line)
   1. Download rcedit.exe from: https://github.com/electron/rcedit/releases
   2. Run in command prompt:
      rcedit.exe "File Rename Mover.exe" --set-icon "app_icon.ico"

Option 3: The icon DOES work in the running application
   - When you run the EXE, the window should show the biohazard icon
   - The taskbar icon should also show the biohazard icon
   - Only File Explorer may not show it

FILES:
------
- File Rename Mover.exe (v1.2.4) - Latest version with version number
- app_icon.ico - The biohazard icon file (keep in same folder as EXE)
- config.json - Application settings (auto-generated)

NOTE: The icon file (app_icon.ico) must stay in the same folder as the EXE
for the window icon to work properly.
