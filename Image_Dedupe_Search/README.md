# Image Dedupe Search

A tool for finding duplicate and similar images using CLIP embeddings and AI-powered similarity detection.

## Version 1.4.0

**Dark Blue Theme** - Modern Qt-based interface with PySide6!

### What's New in v1.4.0
- **Delete All Dupes + Next** button: deletes every duplicate in a group (keeps the representative/green image) and immediately advances to the next group — one click to clear a whole group
- **Keyboard shortcut Ctrl+Shift+D** for Delete All Dupes + Next
- **Startup CLIP model updater**: checks HuggingFace for a newer model revision on launch; prompts to download with progress shown in the status bar (background, non-blocking)
- **Offline mode by default**: `TRANSFORMERS_OFFLINE=1` + `HF_DATASETS_OFFLINE=1` set at startup — prevents hangs on network checks when the model is already cached; the updater worker is the only thing that goes online
- **Thumbnail size max 400px** (was 300px); thumbnail cell height increased for clean two-line labels (filename + %)
- **Improved filename truncation**: scales to actual cell width so long names don't push the similarity % off screen
- **PyInstaller spec**: package metadata for numpy, sentence-transformers, scikit-learn, torch, Pillow bundled to fix import errors in the frozen EXE

### What's New in v1.3.0
- **Multi-Select Bulk Delete**: Select multiple duplicates in the grid and delete them all at once
- **Keyboard Shortcuts**: Press Delete key to remove selected images
- **Improved Compare Dialog**: Navigate between groups with Next/Previous, arrow key support
- **File Size Sorting**: Duplicates sorted by file size (largest first) for easier decisions
- **Better Progress Display**: Clear status messages during embedding computation

### What's New in v1.2.0
- **Search by Image**: Find similar images to any reference image
- **Settings Dialog**: Configure cache location and preferences
- **Embedding Cache**: SQLite-based cache for faster rescans

## Features

### Core Features
- Find duplicate and similar images using CLIP AI embeddings
- Adjustable similarity threshold (0-100%)
- GPU acceleration with CUDA support
- Embedding cache for fast subsequent scans
- Side-by-side image comparison
- Multi-select bulk delete
- Search by reference image
- Real-time progress tracking
- Thumbnail grid with similarity percentages
- Dark blue theme UI

### Supported Image Formats
- JPG/JPEG
- PNG
- BMP
- GIF
- TIFF/TIF
- WebP

## Project Structure

```
Image_Dedupe_Search/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
├── app/
│   ├── core/
│   │   ├── cache.py            # SQLite embedding cache
│   │   ├── embeddings.py       # CLIP embedding engine
│   │   ├── image_utils.py      # Image loading utilities
│   │   └── similarity.py       # Similarity calculations
│   ├── ui/
│   │   ├── main_window.py      # Main application window
│   │   ├── thumbnail_view.py   # Thumbnail grid widget
│   │   ├── image_compare_dialog.py  # Side-by-side comparison
│   │   ├── search_by_image_dialog.py # Search by image feature
│   │   ├── settings_dialog.py  # Settings configuration
│   │   └── styles.py           # Dark blue theme
│   └── workers/
│       ├── scan_worker.py      # File scanning worker
│       ├── embed_worker.py     # Embedding computation worker
│       └── similarity_worker.py # Similarity detection worker
├── ImageDedupeSearch.spec      # PyInstaller spec file
├── build_exe.py                # Build script for executable
└── README.md                   # This file
```

## Usage

### Running the Application

#### From Source
```bash
python main.py
```

#### From Executable
```bash
dist/ImageDedupeSearch/ImageDedupeSearch.exe
```

### Basic Workflow

1. Select a folder containing images to scan
2. Click "Scan" to find all images
3. Wait for embedding computation (uses GPU if available)
4. Adjust similarity threshold as needed
5. Review duplicate groups in the thumbnail grid
6. Use Compare dialog for side-by-side review
7. Delete duplicates individually or in bulk

### Keyboard Shortcuts

- **Delete**: Delete selected images in thumbnail grid
- **Left/Right Arrows**: Navigate between comparisons in Compare dialog
- **Delete** (in Compare): Delete the current duplicate

### Multi-Select Bulk Delete

1. Hold Ctrl and click to select multiple images
2. Hold Shift and click to select a range
3. Click "Delete Selected (N)" button or press Delete key
4. Confirm deletion in the dialog

### Compare Dialog Navigation

- Use Next/Previous buttons to navigate within a group
- At the end of a group, Next moves to the next group
- At the start of a group, Previous moves to the previous group
- Use arrow keys for quick navigation

## Building the Executable

```bash
python build_exe.py
```

The executable will be created at `dist/ImageDedupeSearch/ImageDedupeSearch.exe`.

To distribute, zip the entire `dist/ImageDedupeSearch` folder.

## Configuration

Configuration is stored in `dedupe_config.json` and includes:
- Default scan folder
- Similarity threshold
- Cache path

## Requirements

### For Running from Source
- Python 3.8+
- PySide6
- torch (PyTorch)
- torchvision
- transformers (for CLIP)
- Pillow
- numpy

### Install Dependencies
```bash
pip install PySide6 torch torchvision transformers Pillow numpy
```

### GPU Support
For CUDA acceleration, install PyTorch with CUDA:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Architecture

### Threading Model
- Main thread: UI updates and user interaction
- QThread workers: Scanning, embedding, similarity detection

### Key Components

#### 1. Embedding Engine (`app/core/embeddings.py`)
- Uses OpenAI CLIP model for image embeddings
- GPU acceleration when available
- Batch processing for efficiency

#### 2. Similarity Engine (`app/core/similarity.py`)
- Cosine similarity calculations
- Duplicate group detection
- Threshold-based filtering

#### 3. Embedding Cache (`app/core/cache.py`)
- SQLite-based persistent cache
- Stores embeddings by file path and modification time
- Automatic invalidation when files change

#### 4. UI Components (`app/ui/`)
- **MainWindow**: Main application interface
- **ThumbnailView**: Grid view with multi-select support
- **ImageCompareDialog**: Side-by-side comparison with cross-group navigation
- **SearchByImageDialog**: Find similar images to a reference

## License

MIT License - See LICENSE file for details.

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)

## Version History

### v1.3.0 (January 2026)
- **Multi-Select Bulk Delete**: Select and delete multiple duplicates at once
- **Keyboard Navigation**: Delete key support in grid and compare dialog
- **Arrow Key Navigation**: Left/Right arrows in compare dialog
- **Cross-Group Navigation**: Next/Previous moves between duplicate groups
- **File Size Sorting**: Duplicates sorted largest first
- **Improved Progress Messages**: Clear status during embedding phase

### v1.2.0 (January 2026)
- Search by image feature
- Settings dialog
- Embedding cache with SQLite

### v1.1.0 (January 2026)
- CLIP-based embedding engine
- GPU acceleration
- Similarity threshold slider

### v1.0.0 (January 2026)
- Initial release
- Duplicate image detection
- Thumbnail grid view
- Side-by-side comparison
- Dark blue theme
