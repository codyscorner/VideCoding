#Overview
A desktop GUI tool that scans a folder of images, detects whether the main person is on the left or right side, and flips the image horizontally if the person is on the left. The processed images are saved to an output folder.
The app must be simple, fast, and fully local.

# Tech Stack
- Python 3.10+
- PySide6 for GUI
- OpenCV or Pillow for image manipulation
- Ultralytics YOLOv8n (or similar lightweight model) for person detection
- Threaded worker to keep UI responsive

# Folder Structure

autoflip/
    main.py
    ui/
        main_window.py
    core/
        scanner.py
        detector.py
        flipper.py
        worker.py
    models/
        yolov8n.pt
    output/
	
	
# UI Specification (PySide6)
Main Window Components
- Folder Picker Button
Opens a QFileDialog to select a directory.
- Selected Folder Display
QLabel showing the chosen path.
- Scan & Process Button
Starts background processing.
- Progress Bar
Shows percentage of images processed.
- Log Output
QTextEdit for status messages.
- Optional Preview Area
Shows thumbnails of processed images.


# Core Modules
5.1 scanner.py
Responsibilities:
- Accept folder path
- Recursively find image files (jpg, jpeg, png, webp)
- Return list of file paths

5.2 detector.py
Responsibilities:
- Load YOLO model once at initialization
- For each image:
- Detect persons
- Choose the largest bounding box
- Determine if the person is left or right
Logic:
- Compute bounding box center:
x_center = (x1 + x2) / 2
- Compare to image width:
- < width/2 → left
- >= width/2 → right
Output:
- "left" or "right"
- "none" if no person detected

5.3 flipper.py
Responsibilities:
- Load image
- Flip horizontally if needed
- Save to /output/ with same filename

5.4 worker.py
Responsibilities:
- Run scanning + detection + flipping in a background thread
- Emit:
- progress updates
- log messages
- completion signal
Workflow:
- Scan folder
- For each image:
- Detect person position
- Flip if needed
- Save output
- Emit progress/log
- Emit finished

# Processing Rules
Rule 1 — Only flip if person is on the left
Avoid double‑flipping.
Rule 2 — If no person detected
Skip and log.
Rule 3 — Output naming
- Keep original filename
- Save to /output/

# main.py Responsibilities
- Initialize QApplication
- Load MainWindow
- Connect UI signals to worker
- Start event loop

# Future Enhancements
- Option to flip so person ends up on the left
- Face detection mode
- Preview before saving
- Undo/restore originals
- GPU acceleration toggle


