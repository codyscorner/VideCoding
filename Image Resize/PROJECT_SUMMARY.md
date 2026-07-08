# Image Resizer

**Version:** 1.2.0 | **Status:** Active | **Language:** Python

A desktop batch image resizer that scales images to a target size or percentage, with format and quality controls.

## Features

- Select a source folder of images
- Choose output folder
- Resize by fixed pixel dimensions or percentage scale
- Supports common image formats: JPG, PNG, BMP, GIF, TIFF, WebP
- Configurable JPEG quality
- Progress bar with real-time status
- Persistent settings between sessions
- Dark-themed PyQt6 UI

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow

## Files

```
Image Resize/
├── image_resizer.py          — Main application
├── image_resizer_config.json — Persistent settings
└── ImageResizer.spec         — PyInstaller build spec
```

## Building

```bash
pyinstaller ImageResizer.spec --clean --noconfirm
```

## Future Enhancements

- [ ] Drag-and-drop input
- [ ] Fit/fill/crop-to-aspect modes (e.g., exact 1920×1080 with crop)
- [ ] Sharpening pass after downscale
- [ ] Preserve EXIF option
- [ ] Skip images already at/below target size
