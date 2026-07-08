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
- **Confidence Threshold Slider**: Tune the YOLO body-detection sensitivity (5%-95%); borderline scores land in a third "Unsure" bucket instead of forcing a People/No_People call
- **Review Mode**: Optional thumbnail grid to veto false positives before any file is copied/moved
- **CSV Decision Report**: `sort_report.csv` written to the destination folder listing every file's category, detection pass, confidence, and outcome

## Detection Pipeline

### Pass 1a — HOG face scan (upsample=1)
Fast CPU-parallel scan using the HOG (Histogram of Oriented Gradients) algorithm. Catches large, clear frontal faces quickly. 14 workers run in parallel.

### Pass 1b — HOG face scan (upsample=2)
Slower CPU-parallel HOG scan with 2× upsampling — runs only on images Pass 1a missed. Catches smaller faces and partially visible faces.

### Pass 2 — YOLOv8 body detection (GPU)
Runs only on images both HOG passes missed. Uses YOLOv8n to detect the "person" class at any pose, orientation, and lighting — cyclists, dancers, people from behind, distant figures, side profiles. Runs on GPU if CUDA is available, otherwise CPU. Requires `ultralytics` package.

Detections are bucketed by the confidence slider: scores at or above `threshold + 0.15` are People, scores between `threshold` and `threshold + 0.15` are Unsure, and anything below `threshold` is No_People. Face-pass detections (Pass 1a/1b) have no continuous confidence score and always land in People.

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
├── People/         # Images with confidently detected people
├── Unsure/         # Borderline YOLO body-detection scores near the confidence threshold
├── No_People/      # Images without people
└── sort_report.csv # Per-file decision log (if "Save CSV report" is checked)
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

### v2.1.0
- **Review mode**: optional "Review results before saving" checkbox shows a modal thumbnail grid of every People/Unsure detection before any file is copied/moved; unchecking an image sends it to No_People instead
- **Confidence threshold slider**: tunes YOLO body-detection sensitivity (5%-95%, default 30%), replacing the previously hardcoded constant
- **Third bucket — Unsure folder**: YOLO detections scoring between the threshold and threshold+0.15 land in a new `Unsure` subfolder instead of being forced into People or No_People
- **CSV decision report**: `sort_report.csv` written to the destination folder (toggleable via "Save CSV report of decisions" checkbox) with filename, category, detection pass, confidence, dest path, and success/error per file
- Refactored `face_detector.py` around a single `DetectionEntry` per image so review and CSV reporting share one source of truth instead of parallel bookkeeping

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

- [x] Review mode: thumbnail grid of "person" results to veto false positives before moving
- [x] Confidence threshold slider
- [x] Third bucket: "unsure" folder for borderline scores
- [x] CSV report of decisions per file
