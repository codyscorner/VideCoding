import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PIL import Image
from PIL.ExifTags import TAGS

from app.ui.styles import COLORS

# EXIF tag IDs
_TAG_DATE_TAKEN   = 36867   # DateTimeOriginal
_TAG_DATE_FALLBACK = 306    # DateTime
_TAG_MAKE         = 271
_TAG_MODEL        = 272


def _format_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _format_date(raw: str) -> str:
    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
    try:
        date_part, time_part = raw.strip().split(" ", 1)
        y, m, d = date_part.split(":")
        h, mi, _ = time_part.split(":")
        hour = int(h)
        ampm = "AM" if hour < 12 else "PM"
        hour12 = hour % 12 or 12
        return f"{y}-{m}-{d}  {hour12}:{mi} {ampm}"
    except Exception:
        return raw.strip()


def _read_metadata(path: str) -> dict:
    info = {
        "dimensions": "—",
        "file_size": "—",
        "date_taken": "—",
        "camera": "—",
        "fmt": "—",
    }
    try:
        info["file_size"] = _format_size(os.path.getsize(path))
    except OSError:
        pass

    try:
        with Image.open(path) as img:
            info["dimensions"] = f"{img.width} × {img.height}"
            info["fmt"] = img.format or Path(path).suffix.lstrip(".").upper()

            raw_exif = img._getexif() if hasattr(img, "_getexif") else None
            if raw_exif:
                make  = raw_exif.get(_TAG_MAKE, "").strip()
                model = raw_exif.get(_TAG_MODEL, "").strip()
                # Avoid repeating make in model (e.g. "Apple Apple iPhone 15")
                if make and model.startswith(make):
                    info["camera"] = model
                elif make and model:
                    info["camera"] = f"{make} {model}"
                elif model:
                    info["camera"] = model
                elif make:
                    info["camera"] = make

                date_raw = raw_exif.get(_TAG_DATE_TAKEN) or raw_exif.get(_TAG_DATE_FALLBACK)
                if date_raw:
                    info["date_taken"] = _format_date(date_raw)
    except Exception:
        pass

    return info


class ImageInfoBar(QWidget):
    """Two-line image metadata bar shown at the bottom of the main window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_medium']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(1)

        self._meta_label = QLabel("—")
        self._meta_label.setStyleSheet(
            f"color: {COLORS['fg_secondary']}; font-size: 9pt; background: transparent;"
        )
        layout.addWidget(self._meta_label)

        self._path_label = QLabel("—")
        self._path_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 8pt; background: transparent;"
        )
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._path_label)

    def update_image(self, path: str) -> None:
        info = _read_metadata(path)
        fields = [
            info["dimensions"],
            info["file_size"],
            info["date_taken"],
            info["camera"],
            info["fmt"],
        ]
        meta_text = "   |   ".join(f for f in fields if f and f != "—")
        self._meta_label.setText(f"  {meta_text}"
        )
        self._path_label.setText(f"  {path}")

    def clear(self) -> None:
        self._meta_label.setText("—")
        self._path_label.setText("—")
