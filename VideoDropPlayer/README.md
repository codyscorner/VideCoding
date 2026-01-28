# Video Drop Player

A simple drag-and-drop video player for Windows with playlist support and customizable play order.

## Features

- **Drag & Drop**: Simply drag video files onto the window to play
- **Playlist Support**: Drop multiple files to create a playlist
- **Customizable Play Order**: When dropping multiple files, choose how to sort them:
  - Filename (A-Z or Z-A)
  - Date created (oldest or newest first)
  - Duration (shortest or longest first)
  - Random shuffle
- **Keyboard Controls**: Full playback control via keyboard
- **Dark Theme**: Modern dark blue interface with matching title bar

## Supported Formats

MP4, AVI, MKV, MOV, WMV, FLV, WebM

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Escape | Stop and return to drop screen |
| Left Arrow | Seek backward 5 seconds |
| Right Arrow | Seek forward 5 seconds |
| Up Arrow | Volume up |
| Down Arrow | Volume down |
| M | Toggle mute |
| N | Next video in playlist |
| P | Previous video in playlist |

## Installation

### Option 1: Run the executable
Download `VideoDropPlayer.exe` from the `dist` folder.

### Option 2: Run from source
```bash
pip install -r requirements.txt
python main.py
```

## Building

To build the executable:
```bash
pyinstaller VideoDropPlayer.spec --noconfirm
```

## Requirements

- Python 3.10+
- PyQt6

## Version

1.2.0
