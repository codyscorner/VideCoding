# Photo Gallery

A lightweight desktop image viewer built with PyQt6. Features a vertical filmstrip sidebar for fast browsing, a full-resolution image viewer, EXIF info bar, fullscreen slideshow mode, rating/culling tools, basic edits, and video thumbnails. **The original file is never modified** — all edits are saved as new copies.

## Features

- **Filmstrip sidebar**: vertical thumbnail strip for quick navigation through a folder
- **Full-resolution viewer**: pan/zoom image display with keyboard navigation (left/right arrows)
- **Rating & flagging**: keys 1-5 rate (0 clears), F flags; star/flag badges on thumbnails; "Show" filter (All / Flagged / ★1+ … ★5) for culling keepers from a shoot; persisted to `photo_gallery_ratings.json`
- **Edit ops (copy-only, original untouched)**: rotate (R / Shift+R), crop (drag-select), Save As to a new file — EXIF/ICC preserved. Saving to the original's exact path is blocked.
- **Selection tools**: drag a crop rectangle, then either "Copy Selection" (to clipboard as an image) or "Find Similar (Selection)" (search the folder using that region as the reference, no intermediate file needed)
- **Compare mode**: view two images side by side
- **Delete to Recycle Bin**: Del key or Delete button, with confirmation
- **Video thumbnails**: videos show first-frame thumbnails with a ▶ badge; Enter/double-click plays in the default player
- **Image info bar**: shows filename, dimensions, file size, and EXIF date
- **Slideshow mode**: fullscreen auto-advance with configurable delay and fade transition (still images only)
- **Folder browsing**: open any folder (optionally with subfolders) and browse all supported files
- **Filename search**: filter the filmstrip by filename substring, stacks with the rating/flag filter
- **Find Similar**: pick or paste a reference image (or use a selection from the current photo, see above) to search the folder — face matches (via `face_recognition`) rank first when a face is detected, with an adjustable match-strictness slider; otherwise results rank by visual similarity (color/composition). A background indexer caches fingerprints per folder (SQLite, keyed by path/mtime/size) so re-scans are instant, and searches run off the UI thread with a cancellable progress dialog
- **File context menu**: right-click the viewer for Copy File Path / File Name / Folder Path, Copy File (paste a real copy elsewhere), and Reveal in Explorer
- **Dark theme UI**
- **Config persistence**: last folder, window size, and Find Similar tolerance remembered between sessions

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
| Esc | Cancel selection / compare |

## Usage

```bash
python main.py
```

Or run the built EXE directly.

## Requirements

- Python 3.10+
- PyQt6, Pillow, opencv-python (video thumbnails + similarity histograms), Send2Trash, face_recognition, dlib

```bash
pip install PyQt6 Pillow opencv-python Send2Trash face_recognition dlib
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller PhotoGallery.spec
```

Output: `dist/PhotoGallery/PhotoGallery.exe`

## Version

2.0.0

## Future Enhancements

- [x] Rating/flagging with filter (cull keepers from a shoot) — v1.2.0
- [x] Basic edit ops: rotate, crop, save — v1.2.0
- [x] Compare mode (two images side by side) — v1.2.0
- [x] Delete-to-recycle-bin with confirm — v1.2.0
- [x] Video thumbnails in the filmstrip — v1.2.0
- [x] Resizable filmstrip with scaling thumbnails (drag splitter, width persisted) — v1.3.0
- [x] Filename search + Find Similar (face match / visual similarity) — v2.0.0
- [x] Select Area (copy to clipboard / find similar / save-as), file context menu, copy-only editing (original never overwritten) — v2.0.0
