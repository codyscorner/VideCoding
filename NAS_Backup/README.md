# NAS Backup

**Version:** 1.0.1 | **Status:** Active | **Language:** Python

A desktop backup utility that mirrors source folders to a NAS or any destination drive using dated snapshot folders, with same-day file versioning and automatic retention cleanup.

---

## How It Works

Each backup run creates one dated folder inside the destination:

```
\\NAS\Backup\
  2026-04-11\
    AI\          <- full copy of P:\AI
    Documents\   <- full copy of P:\Documents
  2026-04-10\
    AI\
    Documents\
```

- **Dated folders act as versions** — each day's run is a full snapshot
- **Same-day versioning** — if you run twice in one day and a file changed, the old copy is renamed (`photo_v2026-04-11_091022.jpg`) before the new version is written
- **Retention** — dated folders older than N days are automatically deleted
- **Scheduler support** — run headless via `NAS_Backup.exe --run` from Windows Task Scheduler; all output goes to `Logs\`

---

## Features

- Add multiple source folders to a list — each gets its own subfolder inside the dated destination
- Single destination path — no separate archive folder needed
- Same-day file versioning (optional checkbox) — protects against overwriting changed files on repeated runs
- Configurable retention period (days) and robocopy thread count
- Settings saved to `NAS_Backup_config.json` next to the EXE
- Live status log with robocopy output streamed to the GUI
- CSV log export after each run
- Dark navy theme
- Standalone EXE via PyInstaller

---

## File Structure

```
NAS_Backup/
  main.py            Entry point — GUI or --run headless mode
  main_window.py     PyQt6 GUI
  worker.py          BackupWorker(QThread) — all backup logic
  models.py          BackupRecord dataclass for CSV export
  config.py          ConfigManager — loads/saves NAS_Backup_config.json
  version.py         VERSION = "1.0.1"
  requirements.txt   PyQt6
  NAS_Backup.spec    PyInstaller build spec
  build_exe.bat      One-click EXE builder
  Logs/              Log files written here
```

---

## Requirements

- Python 3.10+
- PyQt6
- Windows (uses robocopy)

```bash
pip install -r requirements.txt
```

---

## Run from Source

```bash
python main.py
```

## Headless Mode (Task Scheduler)

```
NAS_Backup.exe --run
```

Configure sources and destination in the GUI first. The `--run` flag skips the GUI and writes all output to `Logs\`.

---

## Build Standalone EXE

Double-click `build_exe.bat` or run:

```bash
pyinstaller NAS_Backup.spec --clean --noconfirm
```

Output: `dist\NAS_Backup.exe`

---

## Tech Stack

Python · PyQt6 · robocopy · PyInstaller

---

## Changelog

### v1.0.1 — April 11, 2026
- Single dated destination folder structure — one path, no separate archive
- Same-day file versioning — files changed between two runs on the same day are renamed with their timestamp before being overwritten
- Retention deletes dated folders by folder name (YYYY-MM-DD) for reliability
- Removed archive path field from GUI
- Headless --run mode for Windows Task Scheduler

### v1.0.0 — April 11, 2026
- Initial release
