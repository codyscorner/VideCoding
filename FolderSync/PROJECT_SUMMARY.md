# FolderSync

One-way folder sync utility. Compares Source and Destination by filename + filesize, shows what's missing, then copies only those files.

## Features

- Browse-to-select Source and Destination folders
- Optional recursive subfolder inclusion
- Fast two-phase comparison — filename + size match, with optional hash verify for matched-size files
- Reverse Diff mode: find files present in Destination but missing from Source, with confirm-then-delete
- Sortable results table: Name, Size, Reason, Path
- Named sync profiles — save/load/delete a Source + Destination + options combo
- Post-sync/delete summary report, exportable to CSV
- Watch mode: monitors the Source folder and auto-syncs when files change
- Progress bar and live log during sync
- Cancel in-flight operations at any time
- Persists last-used paths across sessions

## Usage

1. Launch `FolderSync.exe` (or `python main.py`)
2. Select a **Source** folder
3. Select a **Destination** folder
4. Toggle **Include subfolders**, **Verify by hash**, or **Watch mode** as needed
5. Choose **Sync** mode (copy missing/changed files) or **Reverse Diff** mode (find extras in Destination)
6. Click **Compare** — differing files appear in the table with a Reason column
7. Click **Sync** (or **Delete Extra** in Reverse Diff mode) to apply the change
8. Click **Export Report (CSV)** to save a record of what was copied or deleted
9. Save frequently-used Source/Destination/option combos as a named **Profile** for quick reuse

## Changelog

### v1.1.0 — 2026-07-08

#### Added
- Optional hash verify (BLAKE2b) — flags same-name/same-size files whose content actually differs
- Reverse Diff mode — finds files in Destination not present in Source, with confirm-then-delete
- Reason column in results table (Missing / Content differs / Extra in Destination)
- Named sync profiles — save, load, and delete Source/Destination/options combos
- Post-sync/delete summary report, exportable to CSV
- Watch mode — monitors the Source folder (and subfolders if recursive) and auto-syncs on change, debounced

### v1.0.0 — 2026-06-27

#### Added
- Initial release
- Source / Destination folder selection with browse dialogs
- Include Subfolders toggle
- Compare phase: fast (name, size) diff displayed in sortable table
- Sync phase: copy missing files with progress bar + live log
- Cancel support during both compare and copy
- Persistent config (last paths, window size)
- PyInstaller spec for windowed EXE build

## Future Enhancements

- [x] Optional hash verify for matched-size files
- [x] Reverse-diff view: files in Destination that aren't in Source (with optional delete)
- [x] Sync profiles (saved source/dest pairs)
- [x] Post-sync summary report with CSV export
- [x] Watch mode: auto-sync when source changes
