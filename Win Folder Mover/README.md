# Windows Folder Mover

**Version:** 1.0.1 | **Status:** Active | **Language:** Python

A desktop utility for recursively moving entire folder trees on Windows, with live progress tracking, detailed per-file logging, and CSV export.

---

## Features

- Recursive folder move with real-time progress bar and live status log
- Background worker thread — UI stays fully responsive during operations
- Windows `MAX_PATH` (260 char) workaround via `\\?\` long-path prefix
- Graceful mid-operation cancel — stops cleanly after the current file
- Per-file metrics tracked: size, time taken, status (Success / Failed / Skipped)
- Specific handling for `PermissionError` (locked files) and `OSError`
- Same-drive moves use `os.rename` (atomic, instant); cross-drive uses copy + delete
- CSV log export with timestamped filename (`move_log_mmddyyyy_hhmm.csv`)
- Smart browse dialogs — each Browse button opens at the folder already set in that field
- Medium red dark theme
- Standalone EXE via PyInstaller

---

## File Structure

```
WinFolderMover/
├── main.py              Entry point
├── main_window.py       GUI only (no file system logic)
├── worker.py            File system logic only (no widget references)
├── models.py            FileRecord dataclass — shared data contract
├── version.py           VERSION = "1.0.1"
├── requirements.txt     PyQt6>=6.6.0
├── WinFolderMover.spec  PyInstaller build spec
└── build_exe.bat        Build script for standalone EXE
```

---

## Requirements

- Python 3.10+
- PyQt6

```bash
pip install -r requirements.txt
```

---

## Run from Source

```bash
python main.py
```

---

## Build Standalone EXE

Double-click `build_exe.bat` or run:

```bash
pip install pyinstaller
pyinstaller WinFolderMover.spec --clean --noconfirm
```

Output: `dist\WinFolderMover.exe`

---

## Tech Stack

Python · PyQt6 · PyInstaller

---

## Changelog

### v1.0.1 — April 11, 2026
- Browse buttons now open at the folder already entered in each field

### v1.0.0 — April 11, 2026
- Initial release
