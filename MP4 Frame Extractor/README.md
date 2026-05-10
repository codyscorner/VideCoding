# MP4 Frame Extractor v1.5

A GUI application for batch-extracting a specific frame from video files and saving them as PNG images.

## Features

- **Source Directory Selection**: Browse and select the folder containing your video files
- **Destination Directory Selection**: Browse and select where to save the extracted frame images
- **Frame Selection**: Choose which frame to extract (1-20, or Last Frame) from each video
- **Video Extension Filter**: Filter by video format (.mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v)
- **Persistent Settings**: Paths and selections are automatically saved and restored between sessions
- **Status Log**: Real-time status updates showing progress and any errors
- **Batch Processing**: Processes all videos in the source directory matching the selected extension
- **Dark Burnt Orange Theme**: Sleek dark UI with burnt orange accents

## Installation

1. Ensure you have Python 3.7+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Using the Executable (Windows)

1. Locate `MP4FrameExtractor.exe` in the `dist` folder.
2. Double-click to launch — your last-used paths and settings are restored automatically.

### From Source Code

```bash
python frame_extractor.py
```

### GUI Instructions

1. Click "Browse..." next to Source Directory to select your video files folder
2. Click "Browse..." next to Destination Directory to select where frames will be saved
3. Select which frame number to extract (default: Last Frame)
4. Select the video file extension to process
5. Click "Extract Frames" to start batch processing

Extracted frames are saved as PNG files:
- Last Frame mode: `{video_name}_LastFrame.png`
- Numbered mode: `{video_name}_frame{N}.png`

## Requirements

- Python 3.7 or higher
- opencv-python 4.8.0 or higher
- PyQt6 6.0 or higher

## Notes

- Frame numbering is 1-based (first frame = 1)
- If the selected frame number exceeds the total frames in a video, that video is skipped
- Settings are saved automatically to `frame_extractor_config.json` next to the executable

## Version History

- **v1.5**: Renamed to MP4 Frame Extractor. Added JSON settings persistence, refactored to standard project structure, new dark burnt orange theme.
- **v1.4**: Migrated UI from tkinter to PyQt6.
- **v1.3**: Added custom UI dark theme (Orange & Black) and refined GUI layout.
- **v1.2**: Added support for extracting the "Last Frame" of videos.
- **v1.0**: Initial release for numeric frame extraction.
