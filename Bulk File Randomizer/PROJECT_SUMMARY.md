# Bulk File Randomizer

**Version:** 1.0.0 | **Status:** Active | **Language:** Python

A desktop utility that copies and renames a batch of files with randomized sequential numbering — useful for shuffling media files before import or processing.

## Features

- Select a source folder of files
- Copy-and-rename all files with randomized sequential numbers
- Configurable output folder and base filename
- Persistent config saved between sessions
- Dark-themed PyQt6 UI

## Tech Stack

- Python 3.10+
- PyQt6

## Files

```
Bulk File Randomizer/
├── main.py         — Entry point
├── renamer.py      — Core copy-and-rename logic
├── config.py       — Config management
├── ui/
│   └── main_window.py  — Main window
└── main_config.json    — Persistent settings
```

## Building

```bash
pyinstaller BulkFileRandomizer.spec --clean --noconfirm
```

Output: `dist/BulkFileRandomizer/BulkFileRandomizer.exe`

## Future Enhancements

- [ ] Dry-run preview table (old name → new name) before copying
- [ ] Move mode in addition to copy
- [ ] Extension filter (only shuffle specific file types)
- [ ] Seeded shuffle: re-use a seed to reproduce the same order
