import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QSplitter, QHBoxLayout, QVBoxLayout, QFileDialog,
    QMessageBox, QDoubleSpinBox, QStatusBar, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QKeyEvent

from config import ConfigManager
from app.ui.styles import STYLESHEET, COLORS
from app.ui.filmstrip import FilmStrip
from app.ui.image_viewer import ImageViewer
from app.ui.image_info_bar import ImageInfoBar
from app.ui.slideshow import SlideshowWindow
from app.workers.thumbnail_worker import ThumbnailWorker, SUPPORTED_EXTENSIONS


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version

        self._image_paths: List[str] = []
        self._current_index: int = -1
        self._thumbnail_worker: Optional[ThumbnailWorker] = None
        self._slideshow_window: Optional[SlideshowWindow] = None

        self.setWindowTitle(f"Photo Gallery v{self.version}")
        self.setMinimumSize(900, 600)
        self.resize(
            self.config.get("window_width", 1200),
            self.config.get("window_height", 750),
        )
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_signals()
        self._load_initial_state()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._filmstrip = FilmStrip(self.config.get("thumbnail_size", 120))
        self._viewer = ImageViewer()
        self._splitter.addWidget(self._filmstrip)
        self._splitter.addWidget(self._viewer)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        root.addWidget(self._splitter, stretch=1)

        root.addWidget(self._build_bottom_bar())

        self._info_bar = ImageInfoBar()
        root.addWidget(self._info_bar)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("Select a folder containing images...")
        layout.addWidget(self._folder_edit, stretch=1)

        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(100)
        self._browse_btn.clicked.connect(self._browse_folder)
        layout.addWidget(self._browse_btn)

        self._subfolders_check = QCheckBox("Include subfolders")
        self._subfolders_check.setStyleSheet(f"color: {COLORS['fg_secondary']}; spacing: 6px;")
        self._subfolders_check.setToolTip("Scan images in all subfolders (useful for photo albums)")
        self._subfolders_check.stateChanged.connect(self._on_subfolder_toggle)
        layout.addWidget(self._subfolders_check)

        layout.addSpacing(16)

        delay_label = QLabel("Delay (s):")
        delay_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(delay_label)

        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.5, 60.0)
        self._delay_spin.setSingleStep(0.5)
        self._delay_spin.setDecimals(1)
        self._delay_spin.setFixedWidth(72)
        self._delay_spin.setToolTip("Time between images in slideshow mode")
        layout.addWidget(self._delay_spin)

        fade_label = QLabel("Fade (s):")
        fade_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(fade_label)

        self._fade_spin = QDoubleSpinBox()
        self._fade_spin.setRange(0.0, 3.0)
        self._fade_spin.setSingleStep(0.5)
        self._fade_spin.setDecimals(1)
        self._fade_spin.setFixedWidth(64)
        self._fade_spin.setToolTip("Fade transition duration between images (0 = instant)")
        layout.addWidget(self._fade_spin)

        self._slideshow_btn = QPushButton("Start Slideshow")
        self._slideshow_btn.setObjectName("slideshow_btn")
        self._slideshow_btn.setEnabled(False)
        self._slideshow_btn.clicked.connect(self._start_slideshow)
        layout.addWidget(self._slideshow_btn)

        return bar

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_medium']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setFixedWidth(90)
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(lambda: self._navigate(-1))
        layout.addWidget(self._prev_btn)

        self._counter_label = QLabel("No images")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter_label.setObjectName("subtitle")
        layout.addWidget(self._counter_label, stretch=1)

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setFixedWidth(90)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(lambda: self._navigate(1))
        layout.addWidget(self._next_btn)

        return bar

    # ── Signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._filmstrip.image_selected.connect(self._on_image_selected)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_initial_state(self) -> None:
        self._delay_spin.setValue(self.config.get("slideshow_delay", 3.0))
        self._fade_spin.setValue(self.config.get("fade_duration", 0.5))
        self._subfolders_check.setChecked(self.config.get("include_subfolders", False))
        last_folder = self.config.get("last_folder", "")
        if last_folder:
            self._folder_edit.setText(last_folder)
            if os.path.isdir(last_folder):
                self._scan_folder(last_folder)

    def _save_config(self) -> None:
        self.config.set("last_folder", self._folder_edit.text())
        self.config.set("slideshow_delay", self._delay_spin.value())
        self.config.set("fade_duration", self._fade_spin.value())
        self.config.set("include_subfolders", self._subfolders_check.isChecked())
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())
        self.config.save()

    # ── Folder Scanning ───────────────────────────────────────────────────────

    @pyqtSlot()
    def _browse_folder(self) -> None:
        existing = self._folder_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", start)
        if folder:
            self._folder_edit.setText(folder)
            self._scan_folder(folder)

    @pyqtSlot()
    def _on_subfolder_toggle(self) -> None:
        folder = self._folder_edit.text().strip()
        if folder and os.path.isdir(folder):
            self._scan_folder(folder)

    def _scan_folder(self, folder: str) -> None:
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            self._thumbnail_worker.cancel()
            self._thumbnail_worker.wait()

        root = Path(folder)
        recursive = self._subfolders_check.isChecked()
        try:
            if recursive:
                entries = sorted(
                    p for ext in SUPPORTED_EXTENSIONS
                    for p in root.rglob(f"*{ext}")
                    if p.is_file()
                )
            else:
                entries = sorted(p for p in root.iterdir() if p.is_file())
        except PermissionError:
            QMessageBox.critical(self, "Error", f"Cannot read folder:\n{folder}")
            return

        self._image_paths = [
            str(p) for p in entries
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if not self._image_paths:
            self._viewer.clear_image()
            self._filmstrip.populate([])
            self._info_bar.clear()
            self._counter_label.setText("No images found")
            self._slideshow_btn.setEnabled(False)
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            self.statusBar().showMessage("No supported images in this folder.")
            return

        self._filmstrip.populate(self._image_paths)
        self._current_index = 0
        self._show_image(0)

        self._thumbnail_worker = ThumbnailWorker(
            self._image_paths,
            thumbnail_size=self.config.get("thumbnail_size", 120),
        )
        self._thumbnail_worker.thumbnail_ready.connect(self._filmstrip.set_thumbnail)
        self._thumbnail_worker.finished.connect(self._on_thumbnails_done)
        self._thumbnail_worker.error.connect(self._on_worker_error)
        self._thumbnail_worker.start()

        self.statusBar().showMessage(
            f"Loading thumbnails for {len(self._image_paths)} images..."
        )

    # ── Image Display ─────────────────────────────────────────────────────────

    def _show_image(self, index: int) -> None:
        if 0 <= index < len(self._image_paths):
            self._current_index = index
            path = self._image_paths[index]
            self._viewer.show_image(path)
            self._filmstrip.select_index(index)
            self._info_bar.update_image(path)
            self._update_nav_controls()

    def _update_nav_controls(self) -> None:
        total = len(self._image_paths)
        has_images = total > 0
        idx = self._current_index
        self._prev_btn.setEnabled(has_images and idx > 0)
        self._next_btn.setEnabled(has_images and idx < total - 1)
        self._slideshow_btn.setEnabled(has_images)
        if has_images and 0 <= idx < total:
            name = Path(self._image_paths[idx]).name
            self._counter_label.setText(f"{idx + 1} of {total}  —  {name}")
        else:
            self._counter_label.setText("No images")

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def _on_image_selected(self, index: int) -> None:
        self._show_image(index)

    def _navigate(self, delta: int) -> None:
        new_index = self._current_index + delta
        new_index = max(0, min(new_index, len(self._image_paths) - 1))
        if new_index != self._current_index:
            self._show_image(new_index)

    @pyqtSlot()
    def _on_thumbnails_done(self) -> None:
        self.statusBar().showMessage(
            f"Ready — {len(self._image_paths)} images loaded.", 5000
        )
        self._thumbnail_worker = None

    @pyqtSlot(str)
    def _on_worker_error(self, message: str) -> None:
        self.statusBar().showMessage(f"Thumbnail error: {message}")
        self._thumbnail_worker = None

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._navigate(-1)
        elif event.key() == Qt.Key.Key_Right:
            self._navigate(1)
        else:
            super().keyPressEvent(event)

    # ── Slideshow ─────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _start_slideshow(self) -> None:
        if not self._image_paths:
            return
        delay = max(0.5, self._delay_spin.value())
        self._slideshow_window = SlideshowWindow(
            image_paths=list(self._image_paths),
            start_index=max(0, self._current_index),
            delay_seconds=delay,
            fade_seconds=self._fade_spin.value(),
        )

    # ── Window Close ──────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            self._thumbnail_worker.cancel()
            self._thumbnail_worker.wait()
        if self._slideshow_window:
            self._slideshow_window.close()
        self._save_config()
        event.accept()
