# Video Frame Extractor

A GUI application for extracting frames from video files and saving them as PNG images.

## Features

- **Source Directory Selection**: Browse and select the folder containing your video files
- **Destination Directory Selection**: Browse and select where to save the extracted frame images
- **Frame Selection**: Choose which frame to extract (1-20) from each video
- **Video Extension Filter**: Filter by video format (.mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v)
- **Status Log**: Real-time status updates showing progress and any errors
- **Batch Processing**: Processes all videos in the source directory matching the selected extension

## Installation

1. Ensure you have Python 3.7+ installed
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:

```bash
python frame_extractor.py
```

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
