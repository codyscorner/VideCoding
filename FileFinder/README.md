# File Finder

A fast full-drive file search utility built with Python and PyQt6. Searches all available drives recursively and streams results in real time.

## Features

- Searches all local and mapped drives simultaneously
- Real-time results as files are found
- Optional minimum file size filter (MB)
- Click any result to copy its full path to the clipboard
- Cancel an in-progress search at any time
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

1. Enter a filename or partial name in the search box
2. (Optional) Set a minimum file size in MB
3. Click **Search** — results appear as they are found
4. Click any result to copy the full path to the clipboard
5. Click **Stop** to cancel

Or run the standalone `dist/FileFinder.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller FileFinder.spec
```

## Version History

| Version | Notes |
|---------|-------|
| v1.0.2 | Current release |
