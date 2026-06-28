# File Copy Move Manager — Features

## Overview

File Copy Move Manager is a companion tool to File Rename Mover. Where File Rename Mover moves and renames files, this tool **copies or moves files without renaming them**, with advanced filtering, flexible organization, and a visual mode system.

- **Gold theme** = Copy Mode (non-destructive, originals kept)
- **Red theme** = Move Mode (source deleted after successful copy + verify)

---

## 1. Dual Operation Mode

### Copy Mode (default, gold theme)
- `shutil.copy2` preserves timestamps and permissions
- Source files never modified
- Safe to re-run — incremental mode skips unchanged files

### Move Mode (red theme)
- Same copy pipeline; on success, `os.remove(source)` is called
- If copy or verify fails, source is preserved and the error is logged
- "Copy Files" / "Copied:" labels update to "Move Files" / "Moved:" throughout the UI
- Mode toggle appears at the top of both tabs and syncs between them

---

## 2. Single Source Tab

One source folder → one destination folder, all settings applied.

Workflow:
1. Browse source + destination
2. Enter file mask(s) and optional filters
3. Set folder organization and duplicate strategy
4. Preview (optional) then Copy/Move

---

## 3. Multi-Source Tab

Run the same copy/move template across **multiple source folders** in sequence.

- Add any number of source folders to a list
- Single destination + single set of options applied to every source
- Each source folder runs as an independent batch; counters accumulate across all
- Useful for consolidating multiple drives or network shares in one pass

---

## 4. File Filtering

### Pattern Masks
- Wildcard support: `*.jpg`, `oct*.*`, `photo_?.png`
- Multiple patterns, comma-separated: `*.jpg, *.png, *.heic`
- Preset dropdown: Images, Videos, Audio, Documents, Archives, Code, Data, All Files (`*.*`)
- Legacy `.jpg` input auto-converted to `*.jpg`

### Size Filter
- Minimum and maximum file size
- Units: B, KB, MB, GB
- Example: copy only files between 1 MB and 4 GB

### Date Filter
- Modified within last N days
- Example: copy only files changed in the last 30 days

---

## 5. Folder Organization

| Option | Destination path example |
|---|---|
| Preserve original structure | `Destination/Photos/2024/vacation.jpg` |
| Flat | `Destination/vacation.jpg` |
| By Year | `Destination/2024/vacation.jpg` |
| By Year/Month | `Destination/2024/08/vacation.jpg` |
| By Year/Month/Day | `Destination/2024/08/15/vacation.jpg` |
| By Date | `Destination/2024-08-15/vacation.jpg` |
| By Month | `Destination/2024-08/vacation.jpg` |

---

## 6. Duplicate Handling

### Number Duplicates (recommended)
Appends `_001`, `_002`, etc. to the destination filename:
```
photo.jpg already exists → photo_001.jpg
```
Never overwrites; all copies are preserved.

### Skip Duplicates
Leaves the existing file untouched and skips the source. Safe for incremental runs when you don't want extra numbered copies.

---

## 7. Preview Window

Click **Preview** to scan files before any operation starts.

- Runs on a background thread; UI stays responsive
- Sortable table: Filename / Size / Full Source Path
- Shows total file count and cumulative size
- **Cancel** — abort; **Proceed** — start the operation immediately using the already-scanned list (no re-scan)
- Respects Incremental mode — files that would be skipped are excluded from the preview

---

## 8. MD5 Checksum Verification

Optional checkbox on each tab. After every file is copied:

1. MD5 hash computed on source (4 MB chunks)
2. MD5 hash computed on destination copy
3. Mismatch → logged as an error, counted in Errors tally

Adds time but guarantees byte-for-byte integrity. Recommended for archival backups.

---

## 9. Incremental Backup Mode

Optional checkbox. Before copying each file, compares:

- File size (bytes must match)
- Modification time (within ±2 s tolerance to handle filesystem rounding)

If both match, the file is skipped (counted as Skipped). Makes repeated runs fast and safe.

---

## 10. Network Path Support

Automatic retry on `OSError` during copy:

- Up to **3 attempts** per file
- **1.5 s delay** between attempts
- Transparent to the user unless all 3 fail
- Covers UNC paths (`\\server\share\...`) and slow or flaky network shares

---

## 11. Progress & Status

### Progress Bars
- **Overall**: current file number / total files
- **Per-file**: chunked progress for files ≥ 50 MB; below threshold the bar flashes 0→100 instantly (fast copy, not meaningful to show)

### Live Counters
Copied / Skipped / Errors update after every single file.

### Status Log
- Quiet by default — only errors, warnings, large-file copies, path truncations, and job timing
- Start time shown at job begin; end time + elapsed (HH:MM:SS.mm) on completion
- Capped at 500 entries; oldest entries drop off automatically
- **Clear Status** clickable label to wipe the log between runs

---

## 12. Large File Handling

Files ≥ 120 MB use a **4 MB chunked copy loop** instead of `shutil.copy2`:

- Real-time per-file progress updates
- Responds to Cancel mid-file
- `shutil.copystat` called after to preserve metadata

Files < 120 MB use `shutil.copy2` (instant, no meaningful per-file progress).

---

## 13. Long Path Handling

Windows MAX_PATH (260 characters) is automatically managed:

- Destination paths that would exceed the limit are truncated
- A `_tr_###` suffix replaces the end of the filename
- Logged in the status box so the user knows which files were affected

---

## 14. Configuration Persistence

All settings saved to `config.json` on close and restored on next launch:

```json
{
  "default_source_folder": "",
  "default_destination_folder": "",
  "last_extension": "*.jpg",
  "preserve_structure": true,
  "folder_structure": "flat",
  "number_duplicates": true,
  "incremental": false,
  "verify_checksum": false,
  "operation_mode": "copy"
}
```

---

## 15. Sorting

Files are scanned, filtered, and sorted **smallest-first** before any copy starts. This ensures fast files finish early and large files are processed last where the per-file progress bar is most useful.

---

## Technical Architecture

| Module | Classes | Responsibility |
|---|---|---|
| `config.py` | `ConfigManager` | JSON load/save/defaults |
| `file_operations.py` | `FileCopier`, `FileScanner`, `FileValidator`, `FileOperationResult` | All copy/move logic |
| `folder_organization.py` | `FolderOrganizer`, `FolderStructure` | Destination path calculation |
| `ui/main_window.py` | `MainWindow` | Tab host, mode sync between tabs |
| `ui/multi_source_tab.py` | `MultiSourceTab` | Multi-folder batch tab |
| `ui/preview_dialog.py` | `PreviewDialog` | Pre-operation file list |
| `ui/styles.py` | `get_stylesheet(mode)`, `COLORS` | Gold + red themes |

---

## Comparison with File Rename Mover

| Aspect | File Rename Mover | File Copy Move Manager |
|---|---|---|
| **Primary action** | Move + rename | Copy or Move (toggle) |
| **Theme** | Red (always) | Gold = copy / Red = move |
| **File naming** | Custom patterns (prefix, datetime, etc.) | Original names preserved |
| **Duplicates** | Error or skip | Number automatically |
| **Folder org** | Date-based only | Preserve original OR 6 date options |
| **Multi-source** | No | Yes (Multi-Source tab) |
| **Backup safe** | No (moves originals) | Yes (Copy Mode) |
| **Best for** | Permanent organization | Backups and bulk moves |
