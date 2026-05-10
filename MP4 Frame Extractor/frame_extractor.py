"""
MP4 Frame Extractor — extracts a specific frame from each video in a folder and saves it as PNG.
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
from ui.styles import STYLESHEET
from config import ConfigManager


class FrameExtractorApp(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self.setWindowTitle("MP4 Frame Extractor v1.5")
        self.setMinimumSize(720, 580)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._restore_settings()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QGridLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("MP4 Frame Extractor")
        title.setObjectName("header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 3)

        # Source directory
        src_label = QLabel("Source Directory:")
        src_label.setObjectName("section")
        layout.addWidget(src_label, 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Folder containing video files...")
        self.source_edit.textChanged.connect(lambda v: self._save_field("source_dir", v))
        layout.addWidget(self.source_edit, 1, 1)
        browse_src = QPushButton("Browse...")
        browse_src.setObjectName("browse_btn")
        browse_src.clicked.connect(self._browse_source)
        layout.addWidget(browse_src, 1, 2)

        # Destination directory
        dst_label = QLabel("Destination Directory:")
        dst_label.setObjectName("section")
        layout.addWidget(dst_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Folder to save extracted frames...")
        self.dest_edit.textChanged.connect(lambda v: self._save_field("dest_dir", v))
        layout.addWidget(self.dest_edit, 2, 1)
        browse_dst = QPushButton("Browse...")
        browse_dst.setObjectName("browse_btn")
        browse_dst.clicked.connect(self._browse_dest)
        layout.addWidget(browse_dst, 2, 2)

        # Frame number
        frame_label = QLabel("Frame Number:")
        frame_label.setObjectName("section")
        layout.addWidget(frame_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        self.frame_combo = QComboBox()
        self.frame_combo.addItems(["Last Frame"] + [str(i) for i in range(1, 21)])
        self.frame_combo.setFixedWidth(140)
        self.frame_combo.currentTextChanged.connect(lambda v: self._save_field("frame_number", v))
        layout.addWidget(self.frame_combo, 3, 1, Qt.AlignmentFlag.AlignLeft)

        # Video extension
        ext_label = QLabel("Video Extension:")
        ext_label.setObjectName("section")
        layout.addWidget(ext_label, 4, 0, Qt.AlignmentFlag.AlignLeft)
        self.ext_combo = QComboBox()
        self.ext_combo.addItems([".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"])
        self.ext_combo.setFixedWidth(120)
        self.ext_combo.currentTextChanged.connect(lambda v: self._save_field("video_extension", v))
        layout.addWidget(self.ext_combo, 4, 1, Qt.AlignmentFlag.AlignLeft)

        # Extract button
        extract_btn = QPushButton("Extract Frames")
        extract_btn.clicked.connect(self._process_videos)
        layout.addWidget(extract_btn, 5, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

        # Status log
        log_label = QLabel("Status Log:")
        log_label.setObjectName("section")
        layout.addWidget(log_label, 6, 0, Qt.AlignmentFlag.AlignLeft)
        self.status_list = QListWidget()
        layout.addWidget(self.status_list, 7, 0, 1, 3)
        layout.setRowStretch(7, 1)
        layout.setColumnStretch(1, 1)

    def _restore_settings(self):
        source = self._config.get("source_dir", "")
        if source:
            self.source_edit.setText(source)

        dest = self._config.get("dest_dir", "")
        if dest:
            self.dest_edit.setText(dest)

        frame = self._config.get("frame_number", "Last Frame")
        idx = self.frame_combo.findText(frame)
        if idx >= 0:
            self.frame_combo.setCurrentIndex(idx)

        ext = self._config.get("video_extension", ".mp4")
        idx = self.ext_combo.findText(ext)
        if idx >= 0:
            self.ext_combo.setCurrentIndex(idx)

        self._log("Ready. Settings restored from last session.")

    def _save_field(self, key: str, value: str):
        self._config.set(key, value)
        self._config.save()

    def _browse_source(self):
        start = self.source_edit.text().strip()
        if not (start and os.path.isdir(start)):
            start = ""
        path = QFileDialog.getExistingDirectory(self, "Select Source Directory", start)
        if path:
            self.source_edit.setText(path)

    def _browse_dest(self):
        start = self.dest_edit.text().strip()
        if not (start and os.path.isdir(start)):
            start = ""
        path = QFileDialog.getExistingDirectory(self, "Select Destination Directory", start)
        if path:
            self.dest_edit.setText(path)

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_list.addItem(f"[{ts}] {message}")
        self.status_list.scrollToBottom()
        QApplication.processEvents()

    def _extract_frame(self, video_path: str, frame_num: str, output_path: str) -> bool:
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._log(f"ERROR: Could not open {os.path.basename(video_path)}")
                return False

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if frame_num == "Last Frame":
                target = max(0, total - 1)
            else:
                try:
                    target = int(frame_num) - 1
                except ValueError:
                    target = 0

            if target >= total > 0:
                self._log(
                    f"WARNING: Frame {target + 1} exceeds total ({total}) "
                    f"in {os.path.basename(video_path)}"
                )
                cap.release()
                return False

            cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            ret, frame = cap.read()

            if not ret and frame_num == "Last Frame" and target > 0:
                for i in range(1, min(5, target + 1)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target - i)
                    ret, frame = cap.read()
                    if ret:
                        break

            label = "Last" if frame_num == "Last Frame" else str(target + 1)
            if ret:
                cv2.imwrite(output_path, frame)
                self._log(f"OK: frame {label} — {os.path.basename(video_path)}")
                cap.release()
                return True
            else:
                self._log(f"ERROR: Could not read frame {label} from {os.path.basename(video_path)}")
                cap.release()
                return False

        except Exception as e:
            self._log(f"ERROR: {e}")
            return False

    def _process_videos(self):
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        frame_num = self.frame_combo.currentText()
        extension = self.ext_combo.currentText()

        if not source or not os.path.isdir(source):
            QMessageBox.critical(self, "Error", "Please select a valid source directory.")
            return

        if not dest:
            QMessageBox.critical(self, "Error", "Please select a destination directory.")
            return

        if not os.path.isdir(dest):
            try:
                os.makedirs(dest, exist_ok=True)
                self._log(f"Created destination: {dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create destination:\n{e}")
                return

        self._log("=" * 60)
        self._log(f"Source:    {source}")
        self._log(f"Dest:      {dest}")
        self._log(f"Frame:     {frame_num}  |  Extension: {extension}")
        self._log("=" * 60)

        videos = [f for f in os.listdir(source) if f.lower().endswith(extension.lower())]
        if not videos:
            self._log(f"WARNING: No {extension} files found in source directory.")
            QMessageBox.warning(self, "No Files", f"No {extension} files found in:\n{source}")
            return

        self._log(f"Found {len(videos)} file(s). Processing...")
        ok = fail = 0

        for video_file in videos:
            video_path = os.path.join(source, video_file)
            base = os.path.splitext(video_file)[0]
            out_name = (
                f"{base}_LastFrame.png" if frame_num == "Last Frame"
                else f"{base}_frame{frame_num}.png"
            )
            if self._extract_frame(video_path, frame_num, os.path.join(dest, out_name)):
                ok += 1
            else:
                fail += 1

        self._log("=" * 60)
        self._log(f"Done — Success: {ok}  |  Failed: {fail}")
        self._log("=" * 60)
        QMessageBox.information(self, "Complete", f"Done!\n\nSuccess: {ok}\nFailed: {fail}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    config_path = Path(__file__).parent / "frame_extractor_config.json"
    config = ConfigManager(config_path)

    window = FrameExtractorApp(config)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
