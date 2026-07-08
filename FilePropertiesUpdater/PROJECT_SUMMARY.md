# MP4 Metadata Editor

**Version:** 1.2.0 | **Status:** Active | **Language:** Python

A drag-and-drop desktop tool for editing metadata tags embedded in MP4/M4A/MKV files. Drop one or more files onto the window and update only the fields you care about — blank fields are skipped.

## Features

- Drag & drop one or more MP4, M4A, or MKV files at a time
- Edit common metadata fields (title, artist, album, comment, description, etc.)
- Only writes fields that have content — blank fields are left untouched
- File list panel shows all queued files
- **View Current Metadata** — select one queued file to preview its existing tags, with an option to load them into the fields for editing
- **Presets** — save the current field values as a named preset and reload them later for repeat tagging jobs
- **Auto-fill Title from filename** — optional per-file checkbox that derives the Title tag from each file's name (strips leading track numbers and separators) instead of using the shared Title field
- MKV metadata is read/written via `ffprobe`/`ffmpeg` (remux with `-c copy`, no re-encode); MP4/M4A use `mutagen` directly. Editing MKV requires ffmpeg on PATH — a clear error is shown if it's missing.
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

## Changelog

### v1.2.0
- **Show current metadata** — "View Current Metadata" button previews a selected file's existing tags, with a one-click "Load Into Fields" to edit from there
- **Presets** — save/load/delete named tag presets (`tag_presets.json` next to the app)
- **Auto-fill Title from filename** — optional checkbox derives each file's Title tag from its filename (strips leading track numbers, replaces separators with spaces)
- **MKV/M4A support** — M4A already worked via mutagen's MP4 container handling; MKV added via `ffmpeg`/`ffprobe` remux (no re-encode)

### v1.1.0
- Initial tracked release: drag-and-drop MP4 batch metadata editing

## Future Enhancements

- [x] Show current metadata of a selected file before editing
- [x] Template/preset tags to apply repeatedly
- [x] Filename → tag auto-fill rules (e.g., parse title from filename)
- [x] Support MKV/M4A too
