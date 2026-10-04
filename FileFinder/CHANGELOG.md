# File Finder — Changelog

## v1.2.1 — 2026-10-03
- **Fix:** right-click → "Open Containing Folder" opened Explorer's default folder instead of selecting the file.
  - Cause: `QFileDialog.getExistingDirectory` returns `P:/dir`; `os.scandir` appends `\name`, so results came out as `P:/dir\sub\file.txt`. Explorer's `/select,` switch rejects mixed separators and silently falls back to the default folder.
  - Root folders are normalised with `os.path.normpath` when added, when loaded from presets (old presets stored `P:/...`), and again at scan time; every emitted result is normalised too.
  - Explorer is now launched as a raw command string `explorer /select,"<path>"` (same approach as PhotoGallery) so argv quoting can't separate the switch from the path. "Open" also normalises before `os.startfile`.

## v1.2.0
- Search file contents (text match) option, first ~2 MB, binaries skipped
- Right-click on results: Open, Open Containing Folder, Copy Path, Delete File
- Saved search presets in a JSON file next to the app
- Multiple root folders per search ("Search entire computer" default)
