# Image People Sorter

A desktop application that automatically sorts images based on people detection. Images containing people are separated from images without people.

## Features

- **Three-Pass Detection Pipeline**: HOG face scan (fast) → HOG face scan (deep) → YOLOv8 body detection (GPU)
- **Maximum Recall**: Catches frontal faces, partially visible faces, people from behind/side/distance, and unusual orientations
- **Fast Parallel Processing**: 14 CPU workers for HOG passes; YOLOv8 runs on GPU internally
- **Robust Image Loading**: Handles 16-bit images, EXIF rotation, palette-mode PNGs, and unusual PIL modes
- **Flexible File Operations**: Choose to copy or move files to destination folders
- **Recursive Scanning**: Option to scan subdirectories for images
- **Progress Tracking**: Real-time progress bar and status log
- **Cancel Support**: Stop processing at any time with immediate worker cleanup
- **Dark Theme UI**: Modern dark-themed interface

## Detection Pipeline

### Pass 1a — HOG face scan (upsample=1)
Fast CPU-parallel scan using the HOG (Histogram of Oriented Gradients) algorithm. Catches large, clear frontal faces quickly. 14 workers run in parallel.

### Pass 1b — HOG face scan (upsample=2)
Slower CPU-parallel HOG scan with 2× upsampling — runs only on images Pass 1a missed. Catches smaller faces and partially visible faces.

### Pass 2 — YOLOv8 body detection (GPU)
Runs only on images both HOG passes missed. Uses YOLOv8n to detect the "person" class at any pose, orientation, and lighting — cyclists, dancers, people from behind, distant figures, side profiles. Runs on GPU if CUDA is available, otherwise CPU. Requires `ultralytics` package.

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- GIF (.gif)
- TIFF (.tiff, .tif)
- WebP (.webp)

## Usage

1. **Select Source Folder**: Browse to the folder containing images to sort
2. **Select Destination Folder**: Choose where sorted images will be placed
3. **Configure Options**:
   - Check "Search subfolders recursively" to include subdirectories
   - Select "Copy" or "Move" for file operation mode
4. **Click "Sort Images"** to begin processing

### Output Structure

```
Destination Folder/
├── People/      # Images with detected people
└── No_People/   # Images without people
```

## Requirements

- Python 3.10+
- PyQt6
- face_recognition
- dlib-bin
- Pillow
- numpy
- psutil
- ultralytics (for YOLOv8 body detection pass)
- torch (for GPU acceleration)

## Installation

```bash
pip install PyQt6 dlib-bin face_recognition --no-deps face_recognition_models pillow numpy psutil platformdirs ultralytics torch --upgrade
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller ImagePeopleSorter.spec
```

The executable will be created in `dist/ImagePeopleSorter/`.

## Performance

Default: 14 HOG workers (suited for 16-core CPUs like AMD Ryzen 9 series). YOLOv8 runs in the main thread and uses GPU batch-internally — no subprocess overhead. Adjust `MAX_WORKERS_HOG` in `face_detector.py` for different hardware.

## Changelog

### v2.0.0
- **Three-pass detection**: added Pass 1b (HOG upsample=2) and Pass 2 (YOLOv8n person detection) to replace the skipped CNN pass
- **YOLOv8 integration**: catches people at any pose/orientation the face passes miss; GPU-accelerated
- **Robust image loader**: handles 16-bit TIFF (`I`, `F` modes), EXIF rotation, palette-mode PNG, and unusual PIL edge cases via `tobytes()` serialization
- **BrokenExecutor handling**: clean cancellation from subprocess pool crashes no longer hangs the UI
- **Error suppression**: first 3 load errors shown in log; further errors suppressed to avoid flooding

### v1.1.0
- Migrated from tkinter to PyQt6, dark orange/amber theme

### v1.0.0
- Initial release: two-pass detection (HOG + CNN)

## Future Enhancements

- [ ] Review mode: thumbnail grid of "person" results to veto false positives before moving
- [ ] Confidence threshold slider
- [ ] Third bucket: "unsure" folder for borderline scores
- [ ] CSV report of decisions per file
