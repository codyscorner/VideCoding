# Video Frame Extractor v1.3

A GUI application for extracting frames from video files and saving them as PNG images.

## Features

- **Source Directory Selection**: Browse and select the folder containing your video files
- **Destination Directory Selection**: Browse and select where to save the extracted frame images
- **Frame Selection**: Choose which frame to extract (1-20, or Last Frame) from each video
- **Video Extension Filter**: Filter by video format (.mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v)
- **Status Log**: Real-time status updates showing progress and any errors
- **Batch Processing**: Processes all videos in the source directory matching the selected extension
- **Custom UI Theme**: Features a sleek new Orange and Black dark mode interface

## Installation

1. Ensure you have Python 3.7+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

You can run the application either by using the pre-built executable or from the Python source code.

### Using the Executable (Windows)

1. Download or locate `FrameExtractor.exe` in the `dist` folder.
2. Double-click the executable to launch the application.

### From Source Code

1. Run the application:

```bash
python frame_extractor.py
```

### GUI Instructions

2. Use the GUI to:
   - Click "Browse..." next to Source Directory to select your video files folder
   - Click "Browse..." next to Destination Directory to select where frames will be saved
   - Select which frame number to extract (default is frame 1)
   - Select the video file extension to process
   - Click "Extract Frames" to start processing

3. The extracted frames will be saved as PNG files with the naming format:
   `{original_video_name}_frame_{frame_number}.png`

## Requirements

- Python 3.7 or higher
- opencv-python 4.8.0 or higher
- tkinter (usually included with Python)

## Notes

- Frame numbering is 1-based (first frame = 1)
- If the selected frame number exceeds the total frames in a video, that video will be skipped
- The status log shows timestamps and success/failure status for each video processed

## Version History

- **v1.3**: Added custom UI dark theme (Orange & Black) and refined GUI layout.
- **v1.2**: Added support for extracting the "Last Frame" of videos.
- **v1.0**: Initial release for numeric frame extraction.
