# JPG to PNG Converter

**Version:** 1.0.0 | **Status:** Active | **Language:** Python

A simple desktop utility that batch-converts JPG/JPEG images to PNG format.

## Features

- Select a source folder containing JPG/JPEG files
- Choose an output folder for the converted PNGs
- Optional: delete original JPG files after conversion
- Progress bar and file list with real-time status
- Dark navy-themed PyQt6 UI

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow

## Files

```
JPG2PNG_Converter/
├── main.py                 — Main application
└── JPG2PNG_Converter.spec  — PyInstaller build spec
```

## Building

```bash
pyinstaller JPG2PNG_Converter.spec --clean --noconfirm
```
