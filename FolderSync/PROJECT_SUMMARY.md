# FolderSync

One-way folder sync utility. Compares Source and Destination by filename + filesize, shows what's missing, then copies only those files.

## Features

- Browse-to-select Source and Destination folders
- Optional recursive subfolder inclusion
- Fast two-phase comparison — no hashing, just filename + size match
- Sortable results table: Name, Size, Source Path
- Progress bar and live log during sync
- Cancel in-flight operations at any time
- Persists last-used paths across sessions

## Usage

1. Launch `FolderSync.exe` (or `python main.py`)
2. Select a **Source** folder
3. Select a **Destination** folder
4. Toggle **Include subfolders** if needed
5. Click **Compare** — missing files appear in the table
6. Click **Sync** — files are copied to Destination maintaining subfolder structure
7. Click **Compare** again to confirm Destination is up to date

## Changelog

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

- [ ] Optional hash verify for matched-size files
- [ ] Reverse-diff view: files in Destination that aren't in Source (with optional delete)
- [ ] Sync profiles (saved source/dest pairs)
- [ ] Post-sync summary report with CSV export
- [ ] Watch mode: auto-sync when source changes
