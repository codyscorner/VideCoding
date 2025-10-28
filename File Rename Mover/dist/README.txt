FILE RENAME MOVER - Version 1.2.4
==================================

A utility for batch renaming and moving files with sequential numbering.

INSTALLATION:
-------------
No installation required! Just run "File Rename Mover_1.2.4.exe"

IMPORTANT:
----------
Keep the "app_icon.ico" file in the same folder as the EXE.
This is required for the window icon to display properly.

FILES IN THIS FOLDER:
---------------------
- File Rename Mover_1.2.4.exe  - The main application
- app_icon.ico                 - Window icon (must stay with EXE)
- config.json                  - Settings file (auto-created on first run)

FEATURES:
---------
- Move files from source to destination folder
- Rename files with custom prefix and sequential numbering
- Automatic counter continuation (checks existing files)
- Filter by file extension
- Dark red/black themed interface
- Settings dialog for default folders

USAGE:
------
1. Select Source Folder (where your files are)
2. Select Destination Folder (where to move them)
3. Enter file Extension (e.g., .mp4, .jpg)
4. Enter "Rename to" pattern (e.g., MyVideo)
5. Click "Move and Rename"

Files will be renamed as: YourPattern_000001_.ext, YourPattern_000002_.ext, etc.

NOTE ABOUT ICON:
----------------
If the EXE icon doesn't appear in Windows Explorer, try:
- Refresh the folder (press F5)
- Rename the file (this forces Windows to refresh the icon cache)
- The icon WILL appear correctly in the title bar and taskbar when running

Version History:
----------------
v1.2.4 - Icon improvements, version number in title bar
v1.2.3 - Added settings dialog
v1.2.0 - Config file support
v1.0.0 - Initial release
