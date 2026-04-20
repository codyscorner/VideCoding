# FaceFinder

A tool for searching matching faces in image collections using face recognition.

## Version 1.2.0

**Dark Gold/Amber Theme** — PyQt6 UI with native drag-drop and thumbnail results viewer.

## Features

### Core Features
- Face recognition-based image search
- Reference image comparison against entire folders
- Adjustable face match tolerance (0.1 - 1.0)
- Recursive subfolder scanning
- Parallel processing with 10 worker processes for speed
- Real-time progress tracking
- Results viewer with thumbnail grid
- Double-click to open file location in Explorer
- Persistent configuration
- Dark theme UI with yellow accents

### Supported Image Formats
- JPG/JPEG
- PNG
- BMP
- GIF
- TIFF/TIF
- WebP

### Search Options

#### Face Match Tolerance
- Lower values = stricter matching (fewer false positives)
- Higher values = more lenient matching (catches more variations)
- Default: 0.6 (good balance for most use cases)

#### Recursive Search
- Enable to search all subfolders
- Disable to search only the selected folder

## Project Structure

```
FaceFinder/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Main window UI and search logic
│   ├── results_viewer.py       # Results display with thumbnails
│   └── styles.py               # Yellow/Black theme
├── FaceFinder.spec             # PyInstaller spec file
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
dist/FaceFinder/FaceFinder.exe
```

### Basic Workflow

1. Select a reference image containing the face you want to find
2. Select the folder to search in
3. Adjust face match tolerance if needed (default 0.6 works well)
4. Enable/disable recursive search for subfolders
5. Click "Search"
6. View matches in the results viewer with thumbnails
7. Double-click any match to open its location in Explorer

### Example Use Cases

#### Use Case 1: Find All Photos of a Person
**Goal:** Find all photos containing a specific person across your photo library

**Settings:**
- Reference Image: A clear photo of the person's face
- Search Folder: Your main photos folder
- Recursive Search: Enabled
- Tolerance: 0.6 (default)

#### Use Case 2: Strict Face Matching
**Goal:** Find only very close matches (same person, similar angle/lighting)

**Settings:**
- Tolerance: 0.4 (stricter)
- Fewer results but higher confidence

#### Use Case 3: Find Similar-Looking Faces
**Goal:** Find faces that look similar (might include different people)

**Settings:**
- Tolerance: 0.7-0.8 (more lenient)
- More results, may include false positives

## Building the Executable

```bash
python build_exe.py
```

The executable will be created at `dist/FaceFinder/FaceFinder.exe`.

To distribute, zip the entire `dist/FaceFinder` folder.

## Configuration

Configuration is stored in `main_config.json` and includes:
- Default reference image path
- Default search folder
- Tolerance setting
- Recursive search preference

## Requirements

### For Running from Source
- Python 3.10+
- PyQt6
- face_recognition
- dlib-bin
- numpy
- Pillow
- psutil

### Install Dependencies
```bash
pip install PyQt6 dlib-bin face_recognition --no-deps face_recognition_models numpy Pillow platformdirs --upgrade
```

## Architecture

### Threading Model
- Main thread: UI updates and user interaction
- Background thread: Search orchestration
- Process pool: 10 worker processes for parallel face detection

### Key Components

#### 1. Configuration Management (`config.py`)
- **ConfigManager**: Handles loading, saving, and managing preferences
- JSON-based persistence

#### 2. Face Search (`ui/main_window.py`)
- **MainWindow**: Main application interface and search logic
- Parallel processing with ProcessPoolExecutor
- Thread-safe UI updates

#### 3. Results Display (`ui/results_viewer.py`)
- **ResultsViewer**: Thumbnail grid of matching images
- Click to open file location

#### 4. UI Styling (`ui/styles.py`)
- **ThemeManager**: Theme and styling management
- Yellow and black color scheme

## License

MIT License - See LICENSE file for details.

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)

## Version History

### v1.2.0
- Migrated from tkinter to PyQt6
- Dark gold/amber theme
- Native PyQt6 drag-drop (no tkinterdnd2)
- QPixmap thumbnail grid in results viewer
- pyqtSignal for thread-safe search completion
- Clipboard paste support preserved

### v1.0.0 (January 2026)
- Initial release with modular architecture
- Face recognition-based image search
- Parallel processing with 10 worker processes
- Adjustable tolerance slider
- Yellow/black theme
