# MP4 Metadata Editor

A desktop tool for editing MP4 file metadata. Drag and drop one or more MP4 files, fill in only the fields you want to update, and apply to all files at once.

## Features

- Drag-and-drop MP4 files (or click to browse)
- Queue multiple files — apply the same metadata to all at once
- 19 metadata fields: Title, Artist, Album, Genre, Year, Comment, Description, Lyrics, TV show info, and more
- Only fields you fill in are written — blank fields are never overwritten
- Results window shows per-file success/failure
- Dark navy theme
- Packaged as a standalone Windows EXE

## Supported Metadata Fields

Title, Artist, Album Artist, Album, Year, Genre, Composer, Grouping, Copyright, Show, Episode ID, Episode Number, Season Number, Category, Keywords, Comment, Description, Long Description, Lyrics

## Requirements

```
Python 3.x
mutagen
tkinterdnd2  (optional, enables drag-and-drop)
```

```bash
pip install mutagen tkinterdnd2
```

`mutagen` is installed automatically if not present. Drag-and-drop works without `tkinterdnd2` — you can still use the browse button.

## Usage

```bash
python mp4_metadata_editor.py
```

1. Drag MP4 files onto the app or click the drop zone to browse
2. Fill in any metadata fields you want to update
3. Click **Apply to All Files**

Or run the standalone `dist/MP4_Metadata_Editor.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller MP4_Metadata_Editor.spec
```

## Version History

| Version | Notes |
|---------|-------|
| v1.0.0 | Initial release |
