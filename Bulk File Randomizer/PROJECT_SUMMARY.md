# Bulk File Randomizer

**Version:** 1.1.0 | **Status:** Active | **Language:** Python

A desktop utility that copies or moves a batch of files into a subfolder with randomized names — useful for shuffling media files before import or processing.

## Features

- Select a source folder of files
- Copy or move files into a subfolder with randomized names (`prefix_xxxxxxxxxx.ext`)
- Extension filter via File Mask presets (Images / Videos / Audio / Documents, or custom comma-separated patterns)
- **Preview** — dry-run table (source name → new name) before committing; pins a seed so the actual run reproduces exactly what you saw
- **Seeded shuffle** — optional seed field (blank = random); same seed + same files always produces the same names in the same order
- Persistent config saved between sessions
- Dark-themed PyQt6 UI

## Tech Stack

- Python 3.10+
- PyQt6

## Files

```
Bulk File Randomizer/
├── main.py             — Entry point
├── renamer.py          — Core copy/move-and-rename logic (seeded, shared by preview and run)
├── config.py           — Config management
├── ui/
│   ├── main_window.py     — Main window
│   └── preview_dialog.py  — Dry-run preview table
└── main_config.json    — Persistent settings
```

## Building

```bash
pyinstaller BulkFileRandomizer.spec --clean --noconfirm
```

Output: `dist/BulkFileRandomizer/BulkFileRandomizer.exe`

## Future Enhancements

- [x] Dry-run preview table (old name → new name) before copying — v1.1.0
- [x] Move mode in addition to copy — v1.1.0
- [x] Extension filter (only shuffle specific file types) — already covered by the existing File Mask + presets field
- [x] Seeded shuffle: re-use a seed to reproduce the same order — v1.1.0
