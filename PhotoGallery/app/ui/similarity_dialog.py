import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageGrab
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QSlider,
)

from app.ui.styles import STYLESHEET, COLORS
from app.workers.thumbnail_worker import SUPPORTED_EXTENSIONS as GALLERY_EXTENSIONS

REF_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


class SimilarityDialog(QDialog):
    """Pick or paste a reference image to search for similar photos."""

    def __init__(self, parent=None, face_tolerance: float = 0.6, initial_reference_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Find Similar Images")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumSize(420, 460)
        self.reference_path: Optional[str] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        info = QLabel(
            "Choose or paste an image. Photos with a matching face are ranked\n"
            "first; otherwise results are ranked by overall visual similarity."
        )
        info.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        root.addWidget(info)

        self._preview = QLabel("No image selected")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(240)
        self._preview.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']};"
        )
        root.addWidget(self._preview, stretch=1)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        paste_btn = QPushButton("Paste from Clipboard (Ctrl+V)")
        paste_btn.clicked.connect(self._paste_from_clipboard)
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(paste_btn)
        root.addLayout(btn_row)

        tol_row = QHBoxLayout()
        tol_label = QLabel("Face match strictness:")
        tol_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        tol_row.addWidget(tol_label)
        self._tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self._tolerance_slider.setRange(30, 90)  # face_recognition distance *100; lower = stricter
        self._tolerance_slider.setValue(int(face_tolerance * 100))
        self._tolerance_slider.setToolTip(
            "Lower = only near-identical faces match. Higher = looser, more (and possibly wrong) matches."
        )
        self._tolerance_slider.valueChanged.connect(self._on_tolerance_changed)
        tol_row.addWidget(self._tolerance_slider, stretch=1)
        self._tolerance_value_label = QLabel(f"{face_tolerance:.2f}")
        self._tolerance_value_label.setMinimumWidth(40)
        tol_row.addWidget(self._tolerance_value_label)
        root.addLayout(tol_row)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self._search_btn = QPushButton("Search")
        self._search_btn.setObjectName("slideshow_btn")
        self._search_btn.setEnabled(False)
        self._search_btn.clicked.connect(self.accept)
        action_row.addWidget(cancel_btn)
        action_row.addWidget(self._search_btn)
        root.addLayout(action_row)

        if initial_reference_path:
            self._set_reference(initial_reference_path)

    @property
    def face_tolerance(self) -> float:
        return self._tolerance_slider.value() / 100

    def _on_tolerance_changed(self, value: int) -> None:
        self._tolerance_value_label.setText(f"{value / 100:.2f}")

    def _set_reference(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Invalid Image", "Could not load that image.")
            return
        self.reference_path = path
        self._preview.setPixmap(
            pixmap.scaled(
                self._preview.width() or 380, 240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._search_btn.setEnabled(True)

    def _browse(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(REF_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(self, "Select Reference Image", "", f"Images ({exts})")
        if path:
            self._set_reference(path)

    def _paste_from_clipboard(self) -> None:
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            QMessageBox.critical(self, "Clipboard Error", f"Failed to read clipboard:\n{e}")
            return
        if img is None:
            QMessageBox.information(self, "No Image", "No image found in clipboard.")
            return
        if isinstance(img, list):
            for item in img:
                if isinstance(item, str) and Path(item).suffix.lower() in GALLERY_EXTENSIONS and Path(item).exists():
                    self._set_reference(item)
                    return
            QMessageBox.warning(self, "Invalid Clipboard", "No valid image paths in clipboard.")
            return
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_path = os.path.join(tempfile.gettempdir(), f"photogallery_clipboard_{stamp}.png")
        img.save(temp_path, "PNG")
        self._set_reference(temp_path)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._paste_from_clipboard()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
