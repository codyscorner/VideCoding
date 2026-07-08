# Video Drop Player

A simple drag-and-drop video and image player for Windows with playlist support and customizable play order.

## Features

- **Drag & Drop**: Simply drag video or image files onto the window to play/view
- **Playlist Support**: Drop multiple video files to create a playlist
- **Image Viewer**: Drop one or more images; use arrow keys to navigate between them
- **Customizable Play Order**: When dropping multiple video files, choose how to sort them:
  - Filename (A-Z or Z-A)
  - Date created (oldest or newest first)
  - Duration (shortest or longest first)
  - Random shuffle
- **Keyboard Controls**: Full playback control via keyboard
- **Dark Theme**: Modern dark blue interface with matching title bar

## Supported Formats

**Video:** MP4, AVI, MKV, MOV, WMV, FLV, WebM

**Image:** JPG, PNG, GIF, BMP, WebP, TIFF

## Keyboard Shortcuts

### Video Mode

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

### Image Mode

| Key | Action |
|-----|--------|
| Left Arrow | Previous image |
| Right Arrow | Next image |
| Escape | Return to drop screen |

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

1.3.2

## Future Enhancements

- [ ] Remember last position per file (resume where you left off)
- [ ] Playback speed control
- [ ] A-B loop for a section
- [ ] Screenshot current frame
- [ ] Delete-current-file hotkey (useful when culling clips)
