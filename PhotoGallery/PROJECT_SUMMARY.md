# Photo Gallery

A lightweight desktop image viewer built with PyQt6. Features a vertical filmstrip sidebar for fast browsing, a full-resolution image viewer, EXIF info bar, and a fullscreen slideshow mode.

## Features

- **Filmstrip sidebar**: vertical thumbnail strip for quick navigation through a folder
- **Full-resolution viewer**: pan/zoom image display with keyboard navigation (left/right arrows)
- **Image info bar**: shows filename, dimensions, file size, and EXIF date
- **Slideshow mode**: fullscreen auto-advance with configurable delay and fade transition
- **Folder browsing**: open any folder and browse all supported images inside
- **Dark theme UI**
- **Config persistence**: last folder and window size remembered between sessions

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- GIF (.gif)
- TIFF (.tiff, .tif)
- WebP (.webp)

## Usage

```bash
python main.py
```

Or run the built EXE directly.

## Requirements

- Python 3.10+
- PyQt6
- Pillow

```bash
pip install PyQt6 Pillow
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller PhotoGallery.spec
```

Output: `dist/PhotoGallery/PhotoGallery.exe`

## Version

1.1.0

## Future Enhancements

- [ ] Rating/flagging with filter (cull keepers from a shoot)
- [ ] Basic edit ops: rotate, crop, save
- [ ] Compare mode (two images side by side)
- [ ] Delete-to-recycle-bin with confirm
- [ ] Video thumbnails in the filmstrip
