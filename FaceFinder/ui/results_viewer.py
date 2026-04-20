"""Results viewer dialog with thumbnail grid for FaceFinder"""

import subprocess
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QDialog, QWidget, QLabel, QPushButton,
    QScrollArea, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from ui.styles import COLORS, STYLESHEET

THUMBNAIL_SIZE = 150


class ThumbnailWidget(QWidget):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.setFixedSize(THUMBNAIL_SIZE + 20, THUMBNAIL_SIZE + 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            img_label.setPixmap(pixmap.scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            img_label.setText("[Error]")
            img_label.setStyleSheet(f"color: {COLORS['error']}; background: {COLORS['bg_light']};")

        layout.addWidget(img_label)

        filename = Path(path).name
        if len(filename) > 22:
            filename = filename[:19] + "..."
        name_label = QLabel(filename)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 8pt;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        self.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-radius: 4px;")

    def mouseDoubleClickEvent(self, event):
        if Path(self.path).exists():
            subprocess.Popen(['explorer', '/select,', self.path])

    def enterEvent(self, event):
        self.setStyleSheet(f"background-color: {COLORS['thumb_hover']}; border-radius: 4px; border: 1px solid {COLORS['accent']};")

    def leaveEvent(self, event):
        self.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-radius: 4px;")


class ResultsViewer(QDialog):
    def __init__(self, parent, matches: List[str]):
        super().__init__(parent)
        self.setWindowTitle(f"Match Results — {len(matches)} images found")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)

        header = QLabel(f"Found {len(matches)} matching images")
        header.setObjectName("header")
        layout.addWidget(header)

        hint = QLabel("Double-click an image to open its location in Explorer")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        grid_widget = QWidget()
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(8)

        cols = max(1, 760 // (THUMBNAIL_SIZE + 30))
        for i, path in enumerate(matches):
            row, col = divmod(i, cols)
            self.grid.addWidget(ThumbnailWidget(path), row, col)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
