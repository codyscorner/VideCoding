# Desktop Video Browser

A Windows desktop application for browsing and playing video files, built with Python and PySide6.

## Overview

Split-pane interface: a file list panel on the left shows video files from a selected folder, and an embedded video player on the right lets you preview them instantly. Features a dark gray theme throughout.

## Features

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
python video_browser/app.py
```

## Build EXE

```bash
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico video_browser/app.py
```

## Project Status

In development. See `Video_Browser_PLAN.md` for the full feature roadmap.
