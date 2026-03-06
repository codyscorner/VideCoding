# Picture Flipper

An intelligent image orientation tool that automatically detects people in photos and flips images to ensure they face the desired direction.

## Version 1.3.0

A desktop GUI application that scans folders of images, detects person positions using AI, and optionally flips images so people face a consistent direction.

## Features

### Core Features
- **AI-Powered Person Detection**: Uses YOLOv8n for fast, accurate person detection
- **Smart Image Flipping**: Automatically flips images based on person position
- **Batch Processing**: Process entire folders of images efficiently
- **Reference Face Mode**: Optionally target specific individuals using face recognition
- **Dual Target Side Options**: Flip so people end up on left OR right side
- **Real-time Progress**: Visual progress bar and detailed logging
- **Standalone Executable**: No Python installation required

### UI Enhancements (v1.1.0)
- **Direct Path Entry**: Paste folder paths directly into text fields
- **Clipboard Image Support**: Paste images directly from clipboard as reference face
- **Improved File Browser**: Quick "..." buttons for file/folder selection
- **Visual Feedback**: Thumbnail preview for reference face images
- **Flexible Input**: Drag paths from file explorer or type them manually

## How It Works

1. **Scan**: Recursively finds all images (.jpg, .jpeg, .png, .webp) in selected folder
2. **Detect**: Uses YOLOv8n to detect people in each image
3. **Analyze**: Determines if the person is on the left or right side
4. **Process**:
   - If person is on the wrong side → flip horizontally
   - If person is already on target side → copy unchanged
   - If no person detected → skip with log message
5. **Save**: Outputs to a subfolder with original filenames preserved

## Tech Stack

- **Python 3.10+**
- **PySide6**: Modern Qt6-based GUI
- **Ultralytics YOLOv8n**: Lightweight person detection model
- **OpenCV**: Image processing and manipulation
- **DeepFace** (optional): Reference face matching
- **Threading**: Responsive UI during batch processing

## Project Structure

```
Picture_Fipper/
├── main.py                  # Application entry point
├── ui/
│   └── main_window.py       # Main application window
├── core/
│   ├── scanner.py           # Image file discovery
│   ├── detector.py          # YOLO person detection
│   ├── flipper.py           # Image flipping logic
│   └── worker.py            # Background processing thread
├── models/
│   └── yolov8n.pt          # YOLOv8 nano model
├── launcher_src/           # VBS launcher source
├── dist/
│   └── PictureFlipper.exe  # Standalone executable
├── output/                 # Default output folder
├── PictureFlipper.spec     # PyInstaller build config
├── build_exe.bat           # Build script
├── runtime_hook.py         # PyInstaller hook
└── README.md              # This file
```

## Usage

### Running the Application

#### Option 1: Standalone Executable (Recommended)
```bash
# Windows - No Python required!
PictureFlipper.exe
```

Or use the convenient launcher:
```bash
Launch PictureFlipper.vbs
```

#### Option 2: From Source
```bash
python main.py
```

### Basic Workflow

1. **Select Source Folder**:
   - Click "..." to browse
   - Or paste/type path directly into the text field

2. **Choose Reference Face** (Optional):
   - Click "..." to browse for an image
   - Or click "Paste Image" to use clipboard image
   - Or type/paste file path directly
   - Leave blank to detect any person

3. **Select Target Side**:
   - **Make Person Left**: Flips images so person ends up on left side
   - **Make Person Right**: Flips images so person ends up on right side

4. **Click "Scan & Process"** to start batch processing

5. **Monitor Progress**:
   - Progress bar shows completion percentage
   - Log output displays detailed processing information

6. **Find Results**:
   - Processed images saved to `Flipped/` subfolder inside the source directory
   - Original filenames preserved

### Processing Logic

#### Without Reference Face
- Detects largest person in image
- Determines if person is left or right of center
- Flips if needed to match target side

#### With Reference Face
- Detects all people in image
- Matches faces against reference
- Only processes images containing the reference person
- Ignores images without matching person

## Requirements

### For Standalone Executable
- Windows 10 or later
- No additional requirements!

### For Running from Source
- Python 3.10+
- PySide6
- ultralytics
- opencv-python
- deepface (for reference face mode)
- torch (CPU version sufficient)

```bash
pip install -r requirements.txt
```

### For Building Executable
```bash
pip install pyinstaller
pyinstaller --clean --noconfirm PictureFlipper.spec
```

Or use the build script:
```bash
build_exe.bat
```

## Configuration

The application automatically:
- Downloads YOLOv8n model on first run (if not present)
- Creates output folder if it doesn't exist
- Preserves original images (never modifies source files)
- Logs all operations for transparency

## Use Cases

- **Photo Collections**: Ensure all portrait photos face the same direction
- **Social Media**: Batch process profile pictures for consistency
- **Product Photography**: Standardize product orientation
- **Event Photography**: Organize photos from photoshoots
- **Family Albums**: Create uniform photo layouts
- **Content Creation**: Prepare images for slideshows or videos

## Version History

### v1.3.0 (March 6, 2026)
- Fixed frozen EXE: bundled OpenCV Haar cascade XML files correctly
- Fixed frozen EXE: added pandas to bundle (required by DeepFace)
- Removed splash screen (was causing Tcl/Tk DLL errors on launch)
- Added step-by-step log messages during face mode model loading
- UI now logs folder selection, face selection, and process start to log window

### v1.2.0 (March 6, 2026)
- Source folder scan no longer recurses into subfolders
- Output now saves to a `Flipped/` folder inside the source directory

### v1.1.0 (February 28, 2026)
- Added direct path entry for source folder
- Implemented clipboard image paste for reference face
- Enhanced file path input with editable text fields
- Compact "..." browse buttons for cleaner UI
- Improved user experience with flexible input methods
- Added visual thumbnail preview for reference face

### v1.0.0 (February 2026)
- Initial release
- AI-powered person detection with YOLOv8n
- Reference face matching capability
- Dual target side options (left/right)
- Batch processing with threading
- Standalone executable distribution
- Real-time progress monitoring

## Future Enhancements

- [ ] Preview mode showing before/after comparisons
- [ ] Undo/restore original images
- [ ] Custom output folder selection
- [ ] Face detection mode (without full person)
- [ ] GPU acceleration toggle
- [ ] Drag-and-drop support for folders
- [ ] Multiple reference faces
- [ ] Confidence threshold adjustment
- [ ] Export processing report

## License

MIT License

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)
