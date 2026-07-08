"""Review dialog for Image People Sorter - thumbnail grid to veto false positives"""

from PyQt6.QtWidgets import (
    QDialog, QLabel, QCheckBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image, ImageOps

from ui.styles import STYLESHEET

THUMB_SIZE = 140


def _load_thumbnail(path: str) -> QPixmap:
    """Best-effort thumbnail load; returns a blank pixmap on failure so a
    single unreadable file never breaks the review grid."""
    try:
        img = Image.open(path)
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img = ImageOps.exif_transpose(img)
        img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.BILINEAR)
        w, h = img.size
        qimg = QImage(img.tobytes(), w, h, w * 3, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())
    except Exception:
        pixmap = QPixmap(THUMB_SIZE, THUMB_SIZE)
        pixmap.fill(Qt.GlobalColor.darkGray)
        return pixmap


class ReviewDialog(QDialog):
    """Modal thumbnail grid letting the user veto candidates before they're
    copied/moved. Unchecking an item sends it to No_People instead."""

    CATEGORY_LABELS = {'people': 'People', 'unsure': 'Unsure'}

    def __init__(self, entries: list, parent=None):
        super().__init__(parent)
        self.entries = entries
        self._checkboxes = {}  # path -> QCheckBox

        self.setWindowTitle(f"Review {len(entries)} Detected Image(s)")
        self.setMinimumSize(720, 560)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Uncheck any image that was misdetected — it will be sent to No_People instead.")
        header.setObjectName("subtitle")
        header.setWordWrap(True)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)

        columns = 4
        for i, entry in enumerate(self.entries):
            row, col = divmod(i, columns)
            cell = QVBoxLayout()

            thumb_label = QLabel()
            thumb_label.setPixmap(_load_thumbnail(entry.path))
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.addWidget(thumb_label)

            category_text = self.CATEGORY_LABELS.get(entry.category, entry.category)
            conf_text = f" ({entry.confidence:.2f})" if entry.confidence is not None else ""
            name_label = QLabel(f"{_truncate(entry.path)}\n{category_text}{conf_text}")
            name_label.setObjectName("subtitle")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(True)
            cell.addWidget(name_label)

            checkbox = QCheckBox("Keep")
            checkbox.setChecked(True)
            cell.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            self._checkboxes[entry.path] = checkbox

            cell_widget = QWidget()
            cell_widget.setLayout(cell)
            grid.addWidget(cell_widget, row, col)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: self._set_all(True))
        select_none = QPushButton("Deselect All")
        select_none.clicked.connect(lambda: self._set_all(False))
        btn_row.addWidget(select_all)
        btn_row.addWidget(select_none)
        btn_row.addStretch()

        confirm_btn = QPushButton("Confirm and Continue")
        confirm_btn.clicked.connect(self.accept)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def _set_all(self, checked: bool):
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(checked)

    def get_overrides(self) -> dict:
        """Returns path -> new_category for every unchecked (vetoed) entry."""
        overrides = {}
        for entry in self.entries:
            if not self._checkboxes[entry.path].isChecked():
                overrides[entry.path] = 'no_people'
        return overrides


def _truncate(path: str, max_len: int = 28) -> str:
    import os
    name = os.path.basename(path)
    if len(name) <= max_len:
        return name
    return name[:max_len - 3] + "..."
