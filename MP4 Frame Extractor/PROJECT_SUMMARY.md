# MP4 Frame Extractor v1.6

A GUI application for batch-extracting frame(s) from video files and saving them as PNG or JPG images.

## Features

- **Source Directory Selection**: Browse and select the folder containing your video files
- **Destination Directory Selection**: Browse and select where to save the extracted frame images
- **Flexible Frame Selection**: Last Frame, exact Frame Number, Percent of Duration, Timestamp (mm:ss), or Every N Seconds (Multiple)
- **Contact Sheet Mode**: combine all frames from "Every N Seconds" mode into one grid image per video
- **Frame Preview**: preview the selected frame on the first matching video before running the full batch
- **Output Format**: PNG or JPG (with adjustable JPG quality)
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
3. Choose a Frame Selection mode and enter its value (not needed for Last Frame):
   - **Frame Number**: 1-based frame index, e.g. `5`
   - **Percent of Duration**: `0`-`100`, e.g. `50` for the midpoint
   - **Timestamp (mm:ss)**: `mm:ss`, `hh:mm:ss`, or raw seconds, e.g. `01:23`
   - **Every N Seconds (Multiple)**: interval in seconds, e.g. `5` — extracts one frame every 5s; optionally check "Combine into contact sheet" to merge them into a single grid image per video instead of separate files
4. Click "Preview Frame" to see the selected frame from the first matching video before committing to a full batch
5. Select the video file extension to process, and the output format (PNG or JPG, with a quality slider for JPG)
6. Click "Extract Frames" to start batch processing

Extracted frames are saved as:
- Last Frame mode: `{video_name}_LastFrame.{ext}`
- Single-frame modes (Frame Number/Percent/Timestamp): `{video_name}_frame{N}.{ext}`
- Multiple mode (separate files): `{video_name}_frame{N}.{ext}` per extracted frame
- Multiple mode (contact sheet): `{video_name}_contactsheet.{ext}`

## Requirements

- Python 3.7 or higher
- opencv-python 4.8.0 or higher
- PyQt6 6.0 or higher
- numpy (installed as an opencv-python dependency)

## Notes

- Frame numbering is 1-based (first frame = 1)
- If a computed frame index exceeds the total frames in a video, that video is skipped
- Settings are saved automatically to `frame_extractor_config.json` next to the executable

## Version History

- **v1.6**: Flexible frame selection (Frame Number/Percent/Timestamp/Every N Seconds), contact sheet mode for multi-frame extraction, frame preview button, PNG/JPG output with JPG quality setting.
- **v1.5**: Renamed to MP4 Frame Extractor. Added JSON settings persistence, refactored to standard project structure, new dark burnt orange theme.
- **v1.4**: Migrated UI from tkinter to PyQt6.
- **v1.3**: Added custom UI dark theme (Orange & Black) and refined GUI layout.
- **v1.2**: Added support for extracting the "Last Frame" of videos.
- **v1.0**: Initial release for numeric frame extraction.

## Future Enhancements

All items complete as of v1.6.
