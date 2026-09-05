# Photo Gallery

A lightweight desktop image viewer built with PyQt6. Features a vertical filmstrip sidebar for fast browsing, a full-resolution image viewer, EXIF info bar, fullscreen slideshow mode, rating/culling tools, basic edits, and video thumbnails.

## Features

- **Filmstrip sidebar**: vertical thumbnail strip for quick navigation through a folder
- **Full-resolution viewer**: pan/zoom image display with keyboard navigation (left/right arrows)
- **Rating & flagging**: keys 1-5 rate (0 clears), F flags; star/flag badges on thumbnails; "Show" filter (All / Flagged / ★1+ … ★5) for culling keepers from a shoot; persisted to `photo_gallery_ratings.json`
- **Edit ops**: rotate (R / Shift+R), crop (drag-select), Save (overwrite w/ confirm) or Save As — EXIF/ICC preserved
- **Compare mode**: view two images side by side
- **Delete to Recycle Bin**: Del key or Delete button, with confirmation
- **Video thumbnails**: videos show first-frame thumbnails with a ▶ badge; Enter/double-click plays in the default player
- **Image info bar**: shows filename, dimensions, file size, and EXIF date
- **Slideshow mode**: fullscreen auto-advance with configurable delay and fade transition (still images only)
- **Folder browsing**: open any folder (optionally with subfolders) and browse all supported files
- **Dark theme UI**
- **Config persistence**: last folder and window size remembered between sessions

## Supported Formats

Images: JPEG, PNG, BMP, GIF, TIFF, WebP
Videos (thumbnail + open in player): MP4, AVI, MKV, MOV, WMV, M4V, WebM

## Keyboard Shortcuts

| Key | Action |
| --- | --- |
| ← / → | Previous / next image |
| 1-5 / 0 | Set / clear rating |
| F | Toggle flag |
| R / Shift+R | Rotate right / left |
| Del | Delete to Recycle Bin |
| Enter | Play video in default player |
| Esc | Cancel crop / compare |

## Usage

```bash
python main.py
```

Or run the built EXE directly.

## Requirements

- Python 3.10+
- PyQt6, Pillow, opencv-python (video thumbnails), Send2Trash

```bash
pip install PyQt6 Pillow opencv-python Send2Trash
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller PhotoGallery.spec
```

Output: `dist/PhotoGallery/PhotoGallery.exe`

## Version

1.4.0

## Future Enhancements

- [x] Rating/flagging with filter (cull keepers from a shoot) — v1.2.0
- [x] Basic edit ops: rotate, crop, save — v1.2.0
- [x] Compare mode (two images side by side) — v1.2.0
- [x] Delete-to-recycle-bin with confirm — v1.2.0
- [x] Video thumbnails in the filmstrip — v1.2.0
- [x] Resizable filmstrip with scaling thumbnails (drag splitter, width persisted) — v1.3.0
