"""
MP4 Frame Extractor — extracts frame(s) from each video in a folder and saves them as PNG/JPG.
"""

import cv2  # type: ignore
import numpy as np  # type: ignore
import os
import sys
import math
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QGridLayout,
    QFileDialog, QMessageBox, QCheckBox, QSpinBox,
)
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.styles import STYLESHEET
from config import ConfigManager

MODE_LAST_FRAME = "Last Frame"
MODE_FRAME_NUMBER = "Frame Number"
MODE_PERCENT = "Percent of Duration"
MODE_TIMESTAMP = "Timestamp (mm:ss)"
MODE_MULTIPLE = "Every N Seconds (Multiple)"

MODES = [MODE_LAST_FRAME, MODE_FRAME_NUMBER, MODE_PERCENT, MODE_TIMESTAMP, MODE_MULTIPLE]

MODE_PLACEHOLDERS = {
    MODE_LAST_FRAME: "(not needed)",
    MODE_FRAME_NUMBER: "e.g. 5 (1-based)",
    MODE_PERCENT: "e.g. 50 (0-100)",
    MODE_TIMESTAMP: "e.g. 01:23 or 83.5",
    MODE_MULTIPLE: "interval in seconds, e.g. 5",
}


def parse_timestamp(text: str) -> float:
    text = text.strip()
    if not text:
        raise ValueError("Timestamp value is required.")
    parts = text.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Could not parse timestamp: {text!r}")


def resolve_targets(mode: str, value: str, total: int, fps: float) -> list[int]:
    """Return a list of 0-based frame indices to extract for the given mode/value."""
    if total <= 0:
        return [0]

    if mode == MODE_LAST_FRAME:
        return [total - 1]

    if mode == MODE_FRAME_NUMBER:
        try:
            n = int(value)
        except ValueError:
            raise ValueError(f"Frame number must be an integer, got {value!r}")
        return [n - 1]

    if mode == MODE_PERCENT:
        try:
            pct = float(value)
        except ValueError:
            raise ValueError(f"Percent must be a number, got {value!r}")
        if not (0 <= pct <= 100):
            raise ValueError("Percent must be between 0 and 100.")
        return [int(round((pct / 100) * (total - 1)))]

    if mode == MODE_TIMESTAMP:
        secs = parse_timestamp(value)
        if fps <= 0:
            raise ValueError("Could not read FPS for timestamp-based selection.")
        return [int(secs * fps)]

    if mode == MODE_MULTIPLE:
        try:
            secs = float(value)
        except ValueError:
            raise ValueError(f"Interval must be a number, got {value!r}")
        if secs <= 0:
            raise ValueError("Interval must be greater than 0 seconds.")
        if fps <= 0:
            raise ValueError("Could not read FPS for interval-based selection.")
        step = max(1, int(round(secs * fps)))
        return list(range(0, total, step))

    raise ValueError(f"Unknown selection mode: {mode!r}")


def read_frame_at(cap, index: int):
    """Seek to `index` and read a frame, falling back a few frames if the exact seek fails."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ret, frame = cap.read()
    if not ret and index > 0:
        for i in range(1, min(5, index + 1)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index - i)
            ret, frame = cap.read()
            if ret:
                break
    return ret, frame


def build_contact_sheet(frames: list, columns: int = 4, thumb_width: int = 320):
    """Combine a list of BGR frames into a single grid image."""
    if not frames:
        return None
    cols = min(columns, len(frames))
    rows = math.ceil(len(frames) / cols)

    thumbs = []
    for f in frames:
        h, w = f.shape[:2]
        thumb_h = max(1, int(thumb_width * h / w))
        thumbs.append(cv2.resize(f, (thumb_width, thumb_h)))

    max_h = max(t.shape[0] for t in thumbs)
    padded = []
    for t in thumbs:
        pad = max_h - t.shape[0]
        if pad > 0:
            t = cv2.copyMakeBorder(t, 0, pad, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        padded.append(t)
    while len(padded) < rows * cols:
        padded.append(np.zeros_like(padded[0]))

    grid_rows = [cv2.hconcat(padded[r * cols:(r + 1) * cols]) for r in range(rows)]
    return cv2.vconcat(grid_rows)


def cv2_to_qpixmap(frame) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class FrameExtractorApp(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self.setWindowTitle("MP4 Frame Extractor v1.6")
        self.setMinimumSize(760, 660)
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
        layout.addWidget(title, 0, 0, 1, 4)

        # Source directory
        src_label = QLabel("Source Directory:")
        src_label.setObjectName("section")
        layout.addWidget(src_label, 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Folder containing video files...")
        self.source_edit.textChanged.connect(lambda v: self._save_field("source_dir", v))
        layout.addWidget(self.source_edit, 1, 1, 1, 2)
        browse_src = QPushButton("Browse...")
        browse_src.setObjectName("browse_btn")
        browse_src.clicked.connect(self._browse_source)
        layout.addWidget(browse_src, 1, 3)

        # Destination directory
        dst_label = QLabel("Destination Directory:")
        dst_label.setObjectName("section")
        layout.addWidget(dst_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Folder to save extracted frames...")
        self.dest_edit.textChanged.connect(lambda v: self._save_field("dest_dir", v))
        layout.addWidget(self.dest_edit, 2, 1, 1, 2)
        browse_dst = QPushButton("Browse...")
        browse_dst.setObjectName("browse_btn")
        browse_dst.clicked.connect(self._browse_dest)
        layout.addWidget(browse_dst, 2, 3)

        # Frame selection mode + value
        mode_label = QLabel("Frame Selection:")
        mode_label.setObjectName("section")
        layout.addWidget(mode_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODES)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo, 3, 1)
        self.value_edit = QLineEdit()
        self.value_edit.textChanged.connect(lambda v: self._save_field("frame_value", v))
        layout.addWidget(self.value_edit, 3, 2, 1, 2)

        # Contact sheet (only meaningful in Multiple mode)
        self.contact_sheet_check = QCheckBox("Combine into contact sheet (Multiple mode)")
        self.contact_sheet_check.toggled.connect(lambda v: self._save_field("contact_sheet", v))
        layout.addWidget(self.contact_sheet_check, 4, 0, 1, 4, Qt.AlignmentFlag.AlignLeft)

        # Video extension
        ext_label = QLabel("Video Extension:")
        ext_label.setObjectName("section")
        layout.addWidget(ext_label, 5, 0, Qt.AlignmentFlag.AlignLeft)
        self.ext_combo = QComboBox()
        self.ext_combo.addItems([".avi", ".flv", ".m4v", ".mkv", ".mov", ".mp4", ".webm", ".wmv"])
        self.ext_combo.setFixedWidth(120)
        self.ext_combo.currentTextChanged.connect(lambda v: self._save_field("video_extension", v))
        layout.addWidget(self.ext_combo, 5, 1, Qt.AlignmentFlag.AlignLeft)

        # Output format + JPG quality
        fmt_label = QLabel("Output Format:")
        fmt_label.setObjectName("section")
        layout.addWidget(fmt_label, 5, 2, Qt.AlignmentFlag.AlignRight)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG"])
        self.format_combo.setFixedWidth(90)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        layout.addWidget(self.format_combo, 5, 3, Qt.AlignmentFlag.AlignLeft)

        quality_label = QLabel("JPG Quality:")
        quality_label.setObjectName("section")
        layout.addWidget(quality_label, 6, 2, Qt.AlignmentFlag.AlignRight)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        self.quality_spin.valueChanged.connect(lambda v: self._save_field("jpg_quality", v))
        layout.addWidget(self.quality_spin, 6, 3, Qt.AlignmentFlag.AlignLeft)

        # Preview + Extract buttons
        preview_btn = QPushButton("Preview Frame")
        preview_btn.setObjectName("browse_btn")
        preview_btn.clicked.connect(self._preview_frame)
        layout.addWidget(preview_btn, 7, 0, 1, 2)

        extract_btn = QPushButton("Extract Frames")
        extract_btn.clicked.connect(self._process_videos)
        layout.addWidget(extract_btn, 7, 2, 1, 2)

        # Preview thumbnail
        self.preview_label = QLabel("No preview yet")
        self.preview_label.setObjectName("preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedHeight(180)
        layout.addWidget(self.preview_label, 8, 0, 1, 4)

        # Status log
        log_label = QLabel("Status Log:")
        log_label.setObjectName("section")
        layout.addWidget(log_label, 9, 0, Qt.AlignmentFlag.AlignLeft)
        self.status_list = QListWidget()
        layout.addWidget(self.status_list, 10, 0, 1, 4)
        layout.setRowStretch(10, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

    def _on_mode_changed(self, mode: str):
        self.value_edit.setPlaceholderText(MODE_PLACEHOLDERS.get(mode, ""))
        self.value_edit.setEnabled(mode != MODE_LAST_FRAME)
        self.contact_sheet_check.setEnabled(mode == MODE_MULTIPLE)
        if mode != MODE_MULTIPLE:
            self.contact_sheet_check.setChecked(False)
        self._save_field("selection_mode", mode)

    def _on_format_changed(self, fmt: str):
        self.quality_spin.setEnabled(fmt == "JPG")
        self._save_field("output_format", fmt)

    def _restore_settings(self):
        source = self._config.get("source_dir", "")
        if source:
            self.source_edit.setText(source)

        dest = self._config.get("dest_dir", "")
        if dest:
            self.dest_edit.setText(dest)

        mode = self._config.get("selection_mode", "")
        value = self._config.get("frame_value", "")
        if not mode:
            # Migrate the pre-v1.6 "frame_number" field (either "Last Frame" or a numeric string).
            legacy = self._config.get("frame_number", "Last Frame")
            if legacy == "Last Frame":
                mode, value = MODE_LAST_FRAME, ""
            else:
                mode, value = MODE_FRAME_NUMBER, legacy
        idx = self.mode_combo.findText(mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.value_edit.setText(value)

        ext = self._config.get("video_extension", ".mp4")
        idx = self.ext_combo.findText(ext)
        if idx >= 0:
            self.ext_combo.setCurrentIndex(idx)

        fmt = self._config.get("output_format", "PNG")
        idx = self.format_combo.findText(fmt)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)

        self.quality_spin.setValue(int(self._config.get("jpg_quality", 90)))
        self.contact_sheet_check.setChecked(bool(self._config.get("contact_sheet", False)))

        self._log("Ready. Settings restored from last session.")

    def _save_field(self, key: str, value) -> None:
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

    def _find_videos(self, source: str, extension: str) -> list[str]:
        return sorted(f for f in os.listdir(source) if f.lower().endswith(extension.lower()))

    def _preview_frame(self):
        source = self.source_edit.text().strip()
        extension = self.ext_combo.currentText()
        if not source or not os.path.isdir(source):
            QMessageBox.warning(self, "Preview", "Select a valid source directory first.")
            return

        videos = self._find_videos(source, extension)
        if not videos:
            QMessageBox.warning(self, "Preview", f"No {extension} files found in source directory.")
            return

        video_path = os.path.join(source, videos[0])
        mode = self.mode_combo.currentText()
        value = self.value_edit.text().strip()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            QMessageBox.critical(self, "Preview", f"Could not open {videos[0]}")
            return
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            try:
                targets = resolve_targets(mode, value, total, fps)
            except ValueError as e:
                QMessageBox.critical(self, "Preview", str(e))
                return

            idx = min(targets[0], max(total - 1, 0)) if total > 0 else targets[0]
            ret, frame = read_frame_at(cap, idx)
            if not ret:
                QMessageBox.warning(self, "Preview", f"Could not read frame from {videos[0]}")
                return

            pix = cv2_to_qpixmap(frame)
            self.preview_label.setPixmap(
                pix.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
            extra = f" (+{len(targets) - 1} more frame(s) in Multiple mode)" if len(targets) > 1 else ""
            self._log(f"Preview: {videos[0]} — frame {idx + 1}{extra}")
        finally:
            cap.release()

    def _process_videos(self):
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        extension = self.ext_combo.currentText()
        mode = self.mode_combo.currentText()
        value = self.value_edit.text().strip()
        output_format = self.format_combo.currentText()
        jpg_quality = self.quality_spin.value()
        contact_sheet = self.contact_sheet_check.isChecked() and mode == MODE_MULTIPLE

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
        self._log(f"Mode:      {mode}  |  Value: {value or '(n/a)'}  |  Extension: {extension}")
        self._log(f"Format:    {output_format}" + (f" (quality {jpg_quality})" if output_format == "JPG" else ""))
        self._log("=" * 60)

        videos = self._find_videos(source, extension)
        if not videos:
            self._log(f"WARNING: No {extension} files found in source directory.")
            QMessageBox.warning(self, "No Files", f"No {extension} files found in:\n{source}")
            return

        self._log(f"Found {len(videos)} file(s). Processing...")
        ok = fail = 0
        ext_out = ".jpg" if output_format == "JPG" else ".png"
        save_params = [cv2.IMWRITE_JPEG_QUALITY, jpg_quality] if output_format == "JPG" else []

        for video_file in videos:
            video_path = os.path.join(source, video_file)
            base = os.path.splitext(video_file)[0]
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._log(f"ERROR: Could not open {video_file}")
                fail += 1
                continue
            try:
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                try:
                    targets = resolve_targets(mode, value, total, fps)
                except ValueError as e:
                    self._log(f"ERROR: {video_file}: {e}")
                    fail += 1
                    continue

                valid_targets = [t for t in targets if 0 <= t < total] if total > 0 else targets
                if not valid_targets:
                    self._log(f"WARNING: frame(s) exceed total ({total}) in {video_file}")
                    fail += 1
                    continue

                frames = []
                for t in valid_targets:
                    ret, frame = read_frame_at(cap, t)
                    if ret:
                        frames.append((t, frame))

                if not frames:
                    self._log(f"ERROR: Could not read frame(s) from {video_file}")
                    fail += 1
                    continue

                if len(frames) > 1 and contact_sheet:
                    sheet = build_contact_sheet([f for _, f in frames])
                    out_path = os.path.join(dest, f"{base}_contactsheet{ext_out}")
                    cv2.imwrite(out_path, sheet, save_params)
                    self._log(f"OK: contact sheet ({len(frames)} frames) — {video_file}")
                    ok += 1
                elif len(frames) > 1:
                    for t, frame in frames:
                        out_path = os.path.join(dest, f"{base}_frame{t + 1}{ext_out}")
                        cv2.imwrite(out_path, frame, save_params)
                    self._log(f"OK: {len(frames)} frame(s) — {video_file}")
                    ok += 1
                else:
                    t, frame = frames[0]
                    suffix = "_LastFrame" if mode == MODE_LAST_FRAME else f"_frame{t + 1}"
                    out_path = os.path.join(dest, f"{base}{suffix}{ext_out}")
                    cv2.imwrite(out_path, frame, save_params)
                    self._log(f"OK: frame {t + 1} — {video_file}")
                    ok += 1
            finally:
                cap.release()

        self._log("=" * 60)
        self._log(f"Done — Success: {ok}  |  Failed: {fail}")
        self._log("=" * 60)
        QMessageBox.information(self, "Complete", f"Done!\n\nSuccess: {ok}\nFailed: {fail}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    config_path = (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent) / "frame_extractor_config.json"
    config = ConfigManager(config_path)

    window = FrameExtractorApp(config)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
