# Image Converter

**Version:** 1.0.0 | **Status:** Active | **Language:** Python

Batch-converts images between JPG, PNG, WebP, BMP, and TIFF formats. Supersedes JPG2PNG_Converter.

## Features

- Select a source folder containing images in any supported format
- Choose an output format: PNG, JPG, WebP, BMP, TIFF
- Quality slider for lossy formats (JPG, WebP) — range 1–100
- Output folder defaults to same as source; optionally choose a different destination
- Recursive subfolder support with mirrored directory structure in output
- Skip files already in the target format (avoids re-converting)
- Delete originals after conversion (optional)
- JPEG alpha-channel handling: RGBA/LA images composited onto white background
- Cancel mid-batch
- Progress bar and real-time file log with success/error coloring
- Dark navy PyQt6 UI (same theme as other VibeCoded apps)

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow

## Files

```
ImageConverter/
├── main.py                  — Main application
├── ImageConverter.spec      — PyInstaller build spec
├── app_icon.ico             — App icon
└── PROJECT_SUMMARY.md       — This file
```

## Building

```bash
cd ImageConverter
pyinstaller ImageConverter.spec --clean --noconfirm
```

Output EXE: `dist/ImageConverter.exe`
Deploy to: `P:\Apps\VibeCoded\Image Converter\`

## Notes

- JPG2PNG_Converter (v1.0.0) is the predecessor — this app covers all its functionality and more
- AVIF not included: requires optional pillow-avif-plugin; add later if needed
