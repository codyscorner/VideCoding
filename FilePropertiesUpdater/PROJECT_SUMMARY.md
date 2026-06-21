# MP4 Metadata Editor

**Version:** 1.1.0 | **Status:** Active | **Language:** Python

A drag-and-drop desktop tool for editing metadata tags embedded in MP4 files. Drop one or more MP4 files onto the window and update only the fields you care about — blank fields are skipped.

## Features

- Drag & drop one or more MP4 files at a time
- Edit common metadata fields (title, artist, album, comment, description, etc.)
- Only writes fields that have content — blank fields are left untouched
- File list panel shows all queued files
- Threaded write operation — UI stays responsive
- Dark-themed PyQt6 interface

## Tech Stack

- Python 3.10+
- PyQt6
- mutagen (MP4 tag writing)

## Files

```
FilePropertiesUpdater/
├── mp4_metadata_editor.py  — Main application
└── MP4_Metadata_Editor.spec
```

## Building

```bash
pyinstaller MP4_Metadata_Editor.spec --clean --noconfirm
```
