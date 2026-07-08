# File Finder App

## Version History

### v1.1.0 (June 21, 2026)
- Search mode selector: Contains (substring), Wildcard (*?), Regex
- Regex validation with user-friendly error dialog before search starts
- File type filter: space/comma-separated extensions (e.g. `.jpg .png .pdf`)
- Max size filter (MB) alongside existing min size
- Date modified filters: optional "After" and "Before" with calendar pickers
- Export CSV button: saves results as CSV (File Name, Full Path, Size, Modified) or TXT
- Export button only enabled after a search returns results
- Window resized to 960×650 to accommodate filter row

### v1.0.2 (Earlier)
- Background QThread scanner across all drives
- Min size filter
- Click-to-copy path to clipboard
- Dark green theme

---

# Original Plan

## Overview
A desktop application built with Python and PyQt6 that allows users to search for files across all accessible local and network drives based on a file name search criteria.

## Core Features & Requirements
1. **UI Components:**
   - Text input box for the file name search criteria.
   - Search button to initiate the scan.
   - "Status Window" (Results List) to display the full paths of matching files.
2. **Drive Scanning:**
   - Detect and scan all available local drives and connected network drives.
   - Perform recursive directory traversal.
3. **Resilience to Permissions:**
   - Catch and ignore `Access Denied` (`PermissionError`) errors. The scan must continue seamlessly to the next file/folder without stopping or alerting the user with an error popup.
4. **Clipboard Integration:**
   - Clicking on any row in the status window will automatically copy the full path of the selected file to the system clipboard.

## Architecture & Implementation Details

### 1. Technology Stack
- **Language:** Python 3.x
- **GUI Framework:** PyQt6
- **Standard Libraries:** `os`, `sys`, `pathlib`, `string` (for Windows drives), `concurrent.futures` or PyQt's `QThread`.

### 2. UI Layout & Design (PyQt6)
- **Theme / Aesthetics:** Custom **Dark Green color scheme** applied via PyQt Stylesheets (QSS). The background will be a deep green, with high-contrast accent greens for inputs, rows, and buttons.
- **MainWindow:** inherits from `QMainWindow` or `QWidget`.
- **Layout:** `QVBoxLayout`.
  - Top: `QHBoxLayout` containing a `QLineEdit` (Search Box) and a `QPushButton` (Search Button).
  - Middle: `QListWidget` or `QTableView` (Status/Results Window).
  - Bottom: `QLabel` for general status updates (e.g., "Searching...", "Copied to clipboard!").

### 3. Asynchronous Scanning
To prevent the UI from freezing during potentially long drive scans:
- Use `QThread` with `pyqtSignal` to emit found file paths back to the main UI thread.
- The thread will recursively iterate through drives using `os.walk` or `pathlib.Path.rglob()`.

### 4. Drive Discovery (Windows)
Since this is a Windows OS (based on your system details), the app can rely on:
```python
import os
import string

def get_available_drives():
    available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    return available_drives
```
*(This includes mapped network drives as well).*

### 5. Error Handling Loop
```python
for root, dirs, files in os.walk(drive):
    try:
        # Check files for criteria match
    except PermissionError:
        continue # Ignore Access Denied and move on
```

### 6. Clipboard Action
- Connect the `itemClicked` signal of the `QListWidget` to a custom slot.
- Slot logic: `QApplication.clipboard().setText(item.text())`
- Update bottom status label to show "Copied: <path>".

## Development Phases
- **Phase 1: UI Skeleton:** Build the PyQt6 form interface (Search box, list, button).
- **Phase 2: File System Scanner:** Develop the independent Python logic to list drives and search safely with `try-except` blocks.
- **Phase 3: Threading Integration:** Connect the scanner to the UI using a background `QThread`.
- **Phase 4: Polish & Clipboard:** Add the click-to-copy feature and provide visual feedback to the user when paths are copied.

- **Phase 5: Version:**
  Start with Version 1.0.0 and increment the version number with each release.

- **Phase 6: Build:**   
  Build the app using PyInstaller to create an executable file.

## Future Enhancements

- [ ] Search file contents (text match) as an option
- [ ] Right-click actions on results: open, open folder, copy path, delete
- [ ] Saved search presets
- [ ] Multiple root folders in one search