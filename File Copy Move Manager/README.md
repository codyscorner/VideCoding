# File Copy Move Manager

A powerful dual-mode tool for batch **copying** or **moving** files with flexible folder organization, advanced filtering, and incremental backup support.

## Version 3.3.1

**Gold theme = Copy Mode | Red theme = Move Mode** — instantly distinguishable from the companion File Rename Mover (always red).

---

## What's New

### v3.3.0 — Move Mode
- **Copy/Move toggle** on each tab — switch between Copy Mode (gold theme) and Move Mode (red theme) with a single button; the entire UI repaints to signal the active mode
- In **Move Mode** source files are deleted after a successful copy + verify
- Mode is persisted to `config.json` and restored on next launch

### v3.1.0 — Preview, Checksum & Incremental Backup
- **Preview window** — scan files before any copy/move starts; sortable table shows filename, size, and full path; cancel or proceed
- **MD5 checksum verification** — optional; compares source vs destination hash after each file; mismatches logged as errors
- **Incremental backup mode** — skips files where destination already matches source by size + mtime (±2 s); safe to re-run repeatedly
- **Network path retry** — automatic 3-attempt retry with 1.5 s delay on `OSError`; works transparently for UNC paths and slow shares

### v3.0.0 — Multi-Source Tab & Performance
- **Multi-Source tab** — run the same copy/move template across multiple source folders in one pass
- All-files preset (`*.*`), errors counter, quiet status log, status box cap (500 entries), per-file progress threshold (≥ 50 MB)

---

## Features

### Two Operation Modes
| | Copy Mode | Move Mode |
|---|---|---|
| **Theme** | Gold / yellow | Red |
| **After copy** | Source intact | Source deleted |
| **Safety** | Non-destructive | Destructive — verify before use |

### Two Tabs
- **Single Source** — one source folder → one destination
- **Multi-Source** — list of source folders → one destination, same settings applied to each

### File Filtering
- **File mask / patterns** — wildcard support (`*.jpg`, `oct*.*`), comma-separated, with presets (Images, Videos, Audio, Documents, Archives, Code, Data, All Files)
- **File size filter** — min and max with unit selector (B / KB / MB / GB)
- **Date filter** — modified within last N days

### Folder Organization
| Mode | Result |
|---|---|
| Preserve structure | Exact hierarchy reproduced at destination |
| Flat | All files in one folder |
| By Year | `2025/file.jpg` |
| By Year/Month | `2025/12/file.jpg` |
| By Year/Month/Day | `2025/12/08/file.jpg` |
| By Date | `2025-12-08/file.jpg` |
| By Month | `2025-12/file.jpg` |

### Duplicate Handling
- **Number duplicates** — appends `_001`, `_002`, etc. (default, safest)
- **Skip duplicates** — leaves existing files untouched

### Progress & Status
- Overall progress bar (file count)
- Per-file progress bar for files ≥ 50 MB
- Live counters: Copied / Skipped / Errors (update after every file)
- Quiet status log — only errors, warnings, large-file copies, and job timing
- Start + end timestamps with elapsed time (HH:MM:SS.mm)
- Log capped at 500 entries; oldest drop off automatically

### Copy Quality
- **Chunked I/O** — 4 MB chunks for files ≥ 120 MB; real-time progress and Cancel support
- **MD5 verification** (optional) — post-copy hash comparison
- **Incremental mode** (optional) — skip unchanged files
- **Network retry** — 3 attempts, 1.5 s delay on `OSError`
- **Long path handling** — paths exceeding Windows 260-char limit auto-truncated with `_tr_###` suffix
- **Metadata preserved** — `shutil.copy2` keeps timestamps and permissions

### Configuration Persistence
All settings auto-saved to `config.json` on close and restored on next launch.

---

## Usage

### Running from Source
```
python main.py
```

Requires Python 3.10+ and PyQt6:
```
pip install PyQt6
```

### Basic Workflow
1. Choose **Copy Mode** or **Move Mode** (button at top of each tab)
2. Select source folder and destination folder
3. Enter file pattern(s) — e.g. `*.jpg`, `*.mp4, *.mov`
4. Set optional filters (size, date)
5. Choose folder organization and duplicate handling
6. Click **Preview** to review files first, or **Copy/Move Files** to start immediately

---

## Project Structure

```
File Copy Move Manager/
├── main.py                  # Entry point
├── config.py                # JSON configuration manager
├── file_operations.py       # FileCopier, FileScanner, FileValidator
├── folder_organization.py   # FolderOrganizer, FolderStructure enum
├── ui/
│   ├── main_window.py       # MainWindow — tab host, mode sync
│   ├── multi_source_tab.py  # MultiSourceTab — multi-folder batch
│   ├── preview_dialog.py    # PreviewDialog — pre-copy file list
│   └── styles.py            # Gold + red themes, get_stylesheet(mode)
├── app_icon.ico
├── config.json              # User settings (auto-generated)
├── README.md
├── CHANGELOG.md
├── FEATURES.md
└── PROJECT_SUMMARY.md
```

---

## Use Cases

### 1. Photo Library Backup (non-destructive)
- Mode: Copy | Preserve structure | Number duplicates
- Re-run as many times as needed; incremental mode skips unchanged files

### 2. Consolidate by Date
- Mode: Copy | By Year/Month | Number duplicates
- Pulls scattered files into a chronological hierarchy

### 3. Archive and Clear (move)
- Mode: Move | Preserve structure | Number duplicates
- Files land at destination and are removed from source

### 4. Multi-Drive Consolidation
- Multi-Source tab | Flat | Number duplicates
- Point at five drives; all files land in one output folder with automatic numbering

---

## Version History

| Version | Date | Highlights |
|---|---|---|
| 3.3.1 | 2026-06-28 | Docs sync + build bump |
| 3.3.0 | 2026-06-28 | Move Mode, red theme, mode persistence, renamed from File Copy Manager |
| 3.2.0 | 2026-06-28 | File type presets sorted alphabetically |
| 3.1.2 | 2026-06-21 | Preview → Proceed reuses already-scanned file list (no re-scan) |
| 3.1.1 | 2026-06-21 | Preview respects Incremental mode |
| 3.1.0 | 2026-06-21 | Preview window, MD5 checksum, incremental backup, network retry |
| 3.0.0 | 2026-04-24 | Multi-Source tab, All Files preset, errors counter, quiet log |
| 2.1.0 | 2026-04-19 | PyQt6 migration from tkinter |
| 2.0.3 | 2026-04-03 | Live counters, path truncation, file logging |
| 2.0.1 | 2026-03-29 | Accurate per-file progress for large files |
| 2.0.0 | 2026-01-21 | Background threading, Cancel, file type presets |
| 1.2.0 | 2026-01-01 | Wildcard pattern filtering, multiple patterns |
| 1.1.0 | 2025-12 | Dual progress bars, size + date filters |
| 1.0.0 | 2025-12-08 | Initial release |

---

## Related Projects

- **File Rename Mover** — companion tool for moving and renaming files with custom patterns (always red theme)

## Author

**Cody's Corner** — [@codyscorner](https://github.com/codyscorner)

Contributions with AI assistance by Claude (Anthropic)
