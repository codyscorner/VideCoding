# Folder Backup Archiver

A PyQt6 desktop app that archives any folder into a dated 7-Zip file, verifies its integrity, and generates a SHA-256 hash — no 7-Zip installation required.

## Features

- **Flexible source** — archive any folder: photos, documents, projects, etc.
- **Custom archive name** — editable prefix with the date auto-appended (`prefix_YYYY_MM_DD.7z`)
- **Compression choice** — Store / Fast / Normal / Maximum / Ultra
- **Any destination** — local drive, mapped network drive, or UNC path (`\\NAS\Backups\`)
- **Same-day overwrite** — re-running on the same day replaces that day's archive cleanly
- **Dual verification** — 7-Zip integrity test + SHA-256 hash file saved alongside the archive
- **Live progress bar** — real-time percentage fed from 7-Zip stdout
- **Elapsed time log** — every log entry stamped with `[hh:mm:ss]` from backup start
- **Persistent settings** — source folder, destination, prefix, and compression level saved between runs
- **Run logs** — each session writes a timestamped log to `logs\`
- **Incremental mode** — optionally skip the backup entirely if the source folder hasn't changed since the last run (compares a size+mtime manifest, no full re-hash needed)
- **Backup rotation** — optionally keep only the N most recent archives for a given prefix; older ones (and their `.sha256` sidecars) are deleted automatically after a successful run
- **Completion notifications** — an optional Windows tray notification on backup complete, skipped, or failed

## Requirements

- Windows 10/11
- Python 3.10+ with PyQt6 (`pip install PyQt6`)
- PyInstaller for building the EXE (`pip install pyinstaller`)
- No 7-Zip installation needed — `7za.exe` is bundled in `7z2601-extra\x64\`

## Running from Source

```
pip install -r requirements.txt
python backup_tool.py
```

## Building the EXE

```
build_exe.bat
```

The EXE is output to `dist\FolderBackupArchiver.exe`.

**After building**, copy these alongside the EXE:
```
7z2601-extra\        ← bundled 7-Zip (required)
```

## Usage

1. **Source Folder** — browse to the folder you want to archive
2. **Destination** — type or browse to any local or network path
3. **Archive Name** — edit the prefix or leave the default; date is always appended
4. **Compression** — choose based on content type:
   - *Store* — photos, videos, already-compressed files (fastest)
   - *Fast / Normal* — general purpose
   - *Maximum / Ultra* — documents and text (slowest, smallest)
5. **Options**:
   - *Skip backup if source is unchanged since last run* — if enabled, the app hashes the source folder's file list (path, size, mtime) before archiving; if it matches the manifest saved from the last successful backup of that same folder, the run is skipped with no archive created
   - *Keep last N backups* — set to 0 to keep everything; otherwise, after a successful run, older archives sharing the same prefix are deleted, keeping only the N most recent
   - *Show a notification when the backup finishes or fails* — pops a Windows tray notification in addition to the in-app dialog, useful if the window is minimized
6. Click **Start Backup**

## Output Files

| File | Description |
|------|-------------|
| `prefix_YYYY_MM_DD.7z` | The archive |
| `prefix_YYYY_MM_DD.7z.sha256` | SHA-256 hash file |
| `logs\backup_YYYY_MM_DD_HHMMSS.log` | Session log |

## Settings

`settings.json` is auto-created next to the EXE on first run. Keys:

| Key | Description |
|-----|-------------|
| `last_source_folder` | Last used source path |
| `last_destination_path` | Last used destination path |
| `archive_prefix` | Last used archive name prefix |
| `compression_level` | Last used compression (`store`/`fast`/`normal`/`maximum`/`ultra`) |
| `7zip_path` | Auto-detected path to `7za.exe` |
| `incremental_enabled` | Whether "skip if unchanged" is turned on |
| `rotation_keep_n` | Number of backups to keep per prefix (`0` = keep all) |
| `notifications_enabled` | Whether tray notifications are turned on |
| `source_manifests` | Per-source-folder manifest hash used by incremental mode |
