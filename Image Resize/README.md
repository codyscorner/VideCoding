# Image Resizer

A batch image resizer with a modern dark blue GUI. Select a folder, choose target dimensions and a resize mode, and process all images at once.

## Features

- Batch resize all images in a folder
- Dimension presets: Square, Widescreen (16:9), Portrait, Mobile, Ultrawide, and more
- Custom width/height input
- Three resize modes:
  - **Stretch** — resize to exact dimensions
  - **Fit** — scale down while maintaining aspect ratio
  - **Fit + Pad** — scale to fit, then pad to exact size with a solid color or transparency
- 16+ padding color options including custom color picker
- Output format options: Original, PNG, JPEG, WEBP, BMP
- JPEG/WEBP quality slider (10–100%)
- Real-time progress bar and processing log
- Output saved to a `resized_images/` subfolder
- Packaged as a standalone Windows EXE

## Requirements

```
Python 3.x
customtkinter
Pillow
```

```bash
pip install customtkinter Pillow
```

## Usage

```bash
python main.py
```

1. Click **Browse** to select a source folder
2. Choose a dimension preset or enter custom W/H values
3. Select a resize mode (and padding color if using Fit + Pad)
4. Choose an output format and quality
5. Click **Start Resizing**

Resized images are saved to `<source_folder>/resized_images/`.

Or run the standalone `dist/ImageResizer.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller ImageResizer.spec
```
