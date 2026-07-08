# File Hash Dedupe

A desktop application that finds and removes duplicate files based on content hash (MD5).

## Features

- **Fast Parallel Hashing**: Configurable parallel workers for high-speed file hashing
- **Content-Based Detection**: Identifies duplicates by file content, not just filename
- **Two Dedupe Modes**: Move duplicates to a `Dupes` subfolder, or permanently delete them
- **Recursive Scanning**: Option to scan subdirectories
- **Progress Tracking**: Real-time progress bar and status log
- **Cancellable**: Cancel mid-run at any time

## Usage

1. **Select Source Folder**: Browse to the folder to scan for duplicates
2. **Configure Options**:
   - Check "Search subfolders recursively" if needed
   - Check "Permanently delete duplicates" to skip the Dupes folder and delete directly
3. **Click "Find Duplicates"** to begin processing

### Output — Move Mode (default)

- First occurrence of each unique file stays in place (primary)
- All duplicates are moved to `Source Folder/Dupes/`
- Review the Dupes folder and delete when satisfied

### Output — Permanent Delete Mode

- First occurrence of each unique file stays in place (primary)
- All duplicates are permanently deleted — **cannot be undone**
- A confirmation dialog is shown before processing begins

## Building Executable

```bash
pip install pyinstaller
pyinstaller FileHashDedupe.spec --clean --noconfirm
```

## Version History

### v1.2.0
- Added permanent delete mode — skip Dupes folder and delete duplicates directly
- Fixed UI freeze when processing large duplicate sets (throttled status logging + capped message queue drain per tick)

### v1.1.0
- Configurable hashing worker count
- Config persistence across sessions

### v1.0.0
- Initial release

## Future Enhancements

- [ ] Preview/review screen before delete — pick which copy survives (keep oldest/newest/shortest path rules)
- [ ] Size pre-filter pass (only hash same-size files — big speed win)
- [ ] xxHash or BLAKE3 option, faster than MD5
- [ ] CSV report of duplicate groups
- [ ] Compare two folders mode (dedupe B against A without touching A)
