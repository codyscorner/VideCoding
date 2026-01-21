# Image People Sorter

A desktop application that automatically sorts images based on face detection. Images containing people are separated from images without people.

## Features

- **Fast Parallel Processing**: Uses multiple CPU cores (14 workers by default) for high-speed face detection
- **HOG Face Detection**: Histogram of Oriented Gradients algorithm for reliable frontal face detection
- **Flexible File Operations**: Choose to copy or move files to destination folders
- **Recursive Scanning**: Option to scan subdirectories for images
- **Progress Tracking**: Real-time progress bar and status log
- **Cancel Support**: Stop processing at any time with immediate worker cleanup
- **Dark Theme UI**: Modern dark-themed interface

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
├── People/      # Images with detected faces
└── No_People/   # Images without detected faces
```

## Requirements

- Python 3.10+
- face_recognition
- dlib
- Pillow
- numpy
- psutil

## Installation

```bash
pip install face_recognition pillow numpy psutil
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller ImagePeopleSorter.spec
```

The executable will be created in `dist/ImagePeopleSorter/`.

## Performance

Optimized for multi-core processors. Default configuration uses 14 parallel workers, suitable for 16-core CPUs like AMD Ryzen 9 series. Adjust `MAX_WORKERS_HOG` in `face_detector.py` for different hardware.

## Version

1.0.0
