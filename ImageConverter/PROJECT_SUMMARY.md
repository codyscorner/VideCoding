# Image Converter

**Version:** 1.1.0 | **Status:** Active | **Language:** Python

Batch-converts images between JPG, PNG, WebP, BMP, and TIFF formats. Supersedes JPG2PNG_Converter.

## Features

- Select a source folder containing images in any supported format
- Drag-and-drop a folder or file onto the window to set the source folder
- Choose an output format: PNG, JPG, WebP, BMP, TIFF
- Quality slider for lossy formats (JPG, WebP) — range 1–100
- Output folder defaults to same as source; optionally choose a different destination
- Recursive subfolder support with mirrored directory structure in output
- Skip files already in the target format (avoids re-converting)
- Delete originals after conversion (optional)
- HEIC/HEIF input support (phone photos) via optional `pillow-heif` package
- Resize-on-convert: cap the longest side to a max dimension (aspect-ratio preserved)
- Metadata (EXIF/ICC profile) preserved by default; "Strip metadata" option removes it
- Parallel workers (2-16) to speed up large batches on multi-core machines
- JPEG alpha-channel handling: RGBA/LA images composited onto white background
- Cancel mid-batch
- Progress bar and real-time file log with success/error coloring
- Dark navy PyQt6 UI (same theme as other VibeCoded apps)

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow
- pillow-heif (optional, enables HEIC/HEIF input)

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

- AVIF not included: requires optional pillow-avif-plugin; add later if needed

## Version History

### v1.1.0
- Drag-and-drop a folder or file onto the window to set the source folder
- Resize-on-convert option (max-dimension spinbox, aspect-preserving `Image.thumbnail`)
- HEIC/HEIF input support via `pillow-heif` (optional dependency, gracefully skipped if absent)
- Metadata now preserved by default (EXIF + ICC profile copied through); "Strip metadata" checkbox opts out
- Parallel workers option (2-16, `ThreadPoolExecutor`) for faster large batches

### v1.0.0
- Initial release: batch image conversion between PNG, JPG, WebP, BMP, TIFF
- Quality slider for lossy formats, recursive subfolders, delete originals option
- JPEG alpha-flattening (RGBA → white-background RGB)
- Supersedes JPG2PNG_Converter (v1.0.0) — all JPG2PNG functionality is covered and extended

## Future Enhancements

- [x] Drag-and-drop files/folders
- [x] Resize-on-convert (max dimension cap)
- [x] HEIC input support (phone photos)
- [x] Strip-metadata option
- [x] Parallel workers for large batches
