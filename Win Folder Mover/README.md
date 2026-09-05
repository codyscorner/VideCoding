# Windows Folder Mover

**Version:** 1.1.0 | **Status:** Active | **Language:** Python

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
- Duplicate skip — if a file already exists at the destination with the same size, it is skipped and the source is left intact
- Read-only file support — automatically clears read-only attributes on source and destination before moving (handles old scanned photos and archived files)
- Mapped network drive support — correctly handles drives like `T:\` without the `\\?\` prefix that breaks mapped drives
- Permission denied fallback — if a move is denied, attempts a copy-only fallback and reports it as Copied instead of Failed
- Summary counters — Moved / Copied / Skipped / Failed / Total
- Multi-folder queue — line up several source/destination pairs and run them sequentially in one session
- Dry-run mode — preview a move with a would-move/would-skip/total report, no files touched
- Retry-locked-files pass — after the main pass, automatically retries any failed file once more (handles files that were transiently locked by another process)
- Verify-after-move option — on cross-drive moves, compares destination size to source before deleting the source; leaves the source in place if verification fails
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
├── version.py           VERSION = "1.0.2"
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

### v1.1.0 — July 8, 2026
- Multi-folder queue: "Add to Queue" / "Remove Selected" plus a queue list; Start Move runs every queued job sequentially and aggregates the CSV log across all of them
- Retry-locked-files pass: after the main move pass, any file that failed is retried once more (0.5s delay) before being reported as a final failure
- Verify-after-move option: on cross-drive moves, compares destination file size to source before deleting the source; same-drive moves stay atomic (`os.rename`) and don't need it
- Documented the dry-run mode (implemented in the prior commit, but the changelog/version were not updated at the time)

### v1.0.2 — April 11, 2026
- Duplicate skip — files already at destination with the same size are skipped, source left intact
- Read-only attribute cleared automatically on source and destination before moving
- Fixed permission denied errors on mapped network drives (e.g. `T:\`) by removing incorrect `\\?\` prefix
- Permission denied fallback now copies instead of failing, reported as Copied in summary
- Summary now shows Moved / Copied / Skipped / Failed / Total

### v1.0.1 — April 11, 2026
- Browse buttons now open at the folder already entered in each field

### v1.0.0 — April 11, 2026
- Initial release

## Future Enhancements

All planned enhancements shipped in v1.1.0.
