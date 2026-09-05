# File Finder

A fast full-drive file search utility built with Python and PyQt6. Searches all available drives (or specific folders) recursively and streams results in real time.

**Current version: 1.2.0**

## Features

- Search the entire computer (all local and mapped drives) or specific root folders
- Search modes: **Contains** (substring), **Wildcard** (`*`, `?`), or **Regex** — with a friendly error dialog if a regex is invalid
- Optional content search — matches the search term against each file's text content (first ~2 MB); binary files are detected and skipped
- Filters: file type (space/comma-separated extensions), min/max size (MB), date modified (After/Before with calendar pickers)
- Right-click a result to Open, Open Containing Folder, Copy Path, or Delete File (with confirmation)
- Click a result to copy its full path to the clipboard
- Saved search presets — save, load, and delete named presets (term, mode, filters, content-search toggle, root folders)
- Export results to CSV or TXT (enabled once a search returns results)
- Real-time results as files are found; Cancel an in-progress search at any time
- Dark green theme
- Packaged as a standalone Windows EXE

## Requirements

```
Python 3.x
PyQt6
```

```bash
pip install PyQt6
```

## Usage

```bash
python finder.py
```

1. Enter a search term, choose a mode (Contains / Wildcard / Regex), and optionally enable content search
2. Choose "Search entire computer" or add specific root folders
3. Set optional filters — file type, size, date modified
4. Click **Search** — results stream in as they're found
5. Click a result to copy its path, or right-click for more actions
6. Export results to CSV/TXT, or save the current search as a preset

Or run the standalone `dist/FileFinder.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller FileFinder.spec
```

## Files

`FileFinder_presets.json` (or `finder_presets.json` when run from source) stores saved search presets next to the app.

## Recent Changes

### v1.2.0
- Search file contents (text match) as an option — matches the search term against each file's text content (first ~2 MB); binary files are detected and skipped automatically
- Right-click actions on results: Open, Open Containing Folder, Copy Path, Delete File (with confirmation)
- Saved search presets — save/load/delete named presets to a JSON file next to the app
- Multiple root folders in one search — "Search entire computer" checkbox (default) or add specific root folders

### v1.1.0 (June 21, 2026)
- Search mode selector: Contains (substring), Wildcard (`*`/`?`), Regex, with validation before search starts
- File type filter (space/comma-separated extensions)
- Max size filter (MB) alongside the existing min size
- Date modified filters (After / Before) with calendar pickers
- Export to CSV or TXT
- Window resized to 960×650 to fit the filter row

### v1.0.2 (earlier)
- Background QThread scanner across all drives
- Min size filter, click-to-copy path, dark green theme
