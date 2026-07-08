# Image Resizer

**Version:** 1.3.0 | **Status:** Active | **Language:** Python

A desktop batch image resizer that scales images to a target size or percentage, with format and quality controls.

## Features

- Select a source folder of images (or drag-and-drop a folder/file onto the window)
- Choose output folder
- Resize by fixed pixel dimensions or percentage scale
- Four resize modes: Fit (Pad to Canvas), Fit (No Padding), Fill (Crop to Aspect), Stretch (Ignore Aspect)
- Optional sharpening pass (unsharp mask) applied after resize
- Optional EXIF metadata preservation
- Optional skip of images already at/below the target size (copied as-is, no upscale)
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

- [x] Drag-and-drop input
- [x] Fit/fill/crop-to-aspect modes (e.g., exact 1920×1080 with crop)
- [x] Sharpening pass after downscale
- [x] Preserve EXIF option
- [x] Skip images already at/below target size
