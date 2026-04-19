"""
Video Frame Extractor GUI Application
Extracts specified frames from video files and saves them as PNG images.
"""

import cv2  # type: ignore
import os
import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QGridLayout,
    QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.styles import STYLESHEET  # type: ignore


class FrameExtractorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Frame Extractor v1.3")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QGridLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Title
        title = QLabel("Frame Extractor")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 3)

        # Source directory
        layout.addWidget(QLabel("Source Directory:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.source_edit = QLineEdit()
        layout.addWidget(self.source_edit, 1, 1)
        browse_src = QPushButton("Browse...")
        browse_src.clicked.connect(self.browse_source)
        layout.addWidget(browse_src, 1, 2)

        # Destination directory
        layout.addWidget(QLabel("Destination Directory:"), 2, 0, Qt.AlignmentFlag.AlignLeft)
        self.dest_edit = QLineEdit()
        layout.addWidget(self.dest_edit, 2, 1)
        browse_dst = QPushButton("Browse...")
        browse_dst.clicked.connect(self.browse_destination)
        layout.addWidget(browse_dst, 2, 2)

        # Frame number
        layout.addWidget(QLabel("Frame Number:"), 3, 0, Qt.AlignmentFlag.AlignLeft)
        self.frame_combo = QComboBox()
        self.frame_combo.addItems(["Last Frame"] + [str(i) for i in range(1, 21)])
        self.frame_combo.setFixedWidth(130)
        layout.addWidget(self.frame_combo, 3, 1, Qt.AlignmentFlag.AlignLeft)

        # Video extension
        layout.addWidget(QLabel("Video Extension:"), 4, 0, Qt.AlignmentFlag.AlignLeft)
        self.ext_combo = QComboBox()
        self.ext_combo.addItems([".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"])
        self.ext_combo.setFixedWidth(110)
        layout.addWidget(self.ext_combo, 4, 1, Qt.AlignmentFlag.AlignLeft)

        # Process button
        process_btn = QPushButton("Extract Frames")
        process_btn.clicked.connect(self.process_videos)
        layout.addWidget(process_btn, 5, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

        # Status log
        layout.addWidget(QLabel("Status Log:"), 6, 0, Qt.AlignmentFlag.AlignLeft)
        self.status_list = QListWidget()
        self.status_list.setFont(self.status_list.font())
        self.status_list.setStyleSheet(
            "QListWidget { font-family: Courier; font-size: 10pt; }"
        )
        layout.addWidget(self.status_list, 7, 0, 1, 3)
        layout.setRowStretch(7, 1)
        layout.setColumnStretch(1, 1)

        self.add_status("Application started. Please select directories.")

    def browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        directory = QFileDialog.getExistingDirectory(self, "Select Source Directory", start)
        if directory:
            self.source_edit.setText(directory)
            self.add_status(f"Source directory set: {directory}")

    def browse_destination(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        directory = QFileDialog.getExistingDirectory(self, "Select Destination Directory", start)
        if directory:
            self.dest_edit.setText(directory)
            self.add_status(f"Destination directory set: {directory}")

    def add_status(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_list.addItem(f"[{timestamp}] {message}")
        self.status_list.scrollToBottom()
        QApplication.processEvents()

    def extract_frame(self, video_path: str, frame_num: str, output_path: str) -> bool:
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.add_status(f"ERROR: Could not open video: {os.path.basename(video_path)}")
                return False

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if frame_num == "Last Frame":
                target_frame = max(0, total_frames - 1)
            else:
                try:
                    target_frame = int(frame_num) - 1
                except ValueError:
                    target_frame = 0

            if target_frame >= total_frames > 0:
                self.add_status(
                    f"WARNING: Frame {target_frame + 1} exceeds total frames "
                    f"({total_frames}) in {os.path.basename(video_path)}"
                )
                cap.release()
                return False

            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()

            if not ret and frame_num == "Last Frame" and target_frame > 0:
                for i in range(1, min(5, int(target_frame) + 1)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_frame) - i)
                    ret, frame = cap.read()
                    if ret:
                        self.add_status(f"Note: Had to decrement target frame by {i} to find valid last frame")
                        break

            frame_label = "Last" if frame_num == "Last Frame" else str(target_frame + 1)
            if ret:
                cv2.imwrite(output_path, frame)
                self.add_status(f"SUCCESS: Extracted frame {frame_label} from {os.path.basename(video_path)}")
                cap.release()
                return True
            else:
                self.add_status(f"ERROR: Could not read frame {frame_label} from {os.path.basename(video_path)}")
                cap.release()
                return False

        except Exception as e:
            self.add_status(f"ERROR: {str(e)}")
            return False

    def process_videos(self):
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        frame_num = self.frame_combo.currentText()
        extension = self.ext_combo.currentText()

        if not source or not os.path.isdir(source):
            QMessageBox.critical(self, "Error", "Please select a valid source directory")
            self.add_status("ERROR: Invalid source directory")
            return

        if not dest:
            QMessageBox.critical(self, "Error", "Please select a destination directory")
            self.add_status("ERROR: No destination directory specified")
            return

        if not os.path.isdir(dest):
            try:
                os.makedirs(dest, exist_ok=True)
                self.add_status(f"Created destination directory: {dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create destination directory: {str(e)}")
                self.add_status(f"ERROR: Could not create destination directory: {str(e)}")
                return

        self.add_status("=" * 60)
        self.add_status("Starting batch processing...")
        self.add_status(f"Source: {source}")
        self.add_status(f"Destination: {dest}")
        self.add_status(f"Frame number: {frame_num}")
        self.add_status(f"Extension filter: {extension}")
        self.add_status("=" * 60)

        video_files = [f for f in os.listdir(source) if f.lower().endswith(extension.lower())]

        if not video_files:
            self.add_status(f"WARNING: No {extension} files found in source directory")
            QMessageBox.warning(self, "No Files", f"No {extension} files found in the source directory")
            return

        self.add_status(f"Found {len(video_files)} video file(s)")

        success_count = 0
        fail_count = 0

        for video_file in video_files:
            video_path = os.path.join(source, video_file)
            base_name = os.path.splitext(video_file)[0]
            output_filename = (
                f"{base_name}_LastFrame.png" if frame_num == "Last Frame"
                else f"{base_name}_frame_{frame_num}.png"
            )
            output_path = os.path.join(dest, output_filename)
            self.add_status(f"Processing: {video_file}")

            if self.extract_frame(video_path, frame_num, output_path):
                success_count += 1
            else:
                fail_count += 1

        self.add_status("=" * 60)
        self.add_status("Processing complete!")
        self.add_status(f"Successful: {success_count} | Failed: {fail_count}")
        self.add_status("=" * 60)

        QMessageBox.information(
            self, "Complete",
            f"Processing complete!\nSuccessful: {success_count}\nFailed: {fail_count}"
        )


def main():
    app = QApplication(sys.argv)
    window = FrameExtractorApp()
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
