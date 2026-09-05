# Desktop Video Browser

A Windows desktop application for browsing and playing video files, built with Python and PySide6.

## Overview

Split-pane interface: a file list panel on the left shows video files from a selected folder, and an embedded video player on the right lets you preview them instantly. Features a dark gray theme throughout.

## Features

- Explorer-style folder tree for navigating drives and folders, alongside the file list
- Browse video files in any folder
- Click to play — video loads immediately in the right panel
- Play / Pause / Stop controls
- Drag-and-drop folder loading
- Dark gray theme with blue accents
- Settings persistence (last folder, window geometry)
- Packaged as a standalone Windows EXE

## Tech Stack

- Python 3.10+
- PySide6 (Qt for Python)
- QtMultimedia for video playback
- PyInstaller for EXE packaging

## Requirements

```
Python 3.10+
PySide6
```

```bash
pip install PySide6
```

## Usage

```bash
python app.py
```

## Build EXE

```bash
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico app.py
```

## Roadmap

Ideas not yet built:

- Thumbnail previews in the file list
- Video metadata display (duration, resolution, codec)
- Keyboard shortcuts
- Light theme toggle
- Multi-folder watch list
- Tagging system with a small SQLite index
- Video trimming or frame capture
- AI-powered video tagging / automatic scene detection

## Project Status

In development.
