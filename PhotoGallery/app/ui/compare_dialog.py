from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSplitter, QWidget,
)
from PyQt6.QtCore import Qt

from app.ui.styles import STYLESHEET, COLORS
from app.ui.image_viewer import ImageViewer


class CompareDialog(QDialog):
    """Side-by-side comparison of two images."""

    def __init__(self, left_path: str, right_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Images")
        self.setStyleSheet(STYLESHEET)
        self.resize(1400, 800)
        self.setMinimumSize(800, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_pane(left_path))
        splitter.addWidget(self._build_pane(right_path))
        splitter.setSizes([700, 700])
        root.addWidget(splitter, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(110)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _build_pane(self, path: str) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        name_label = QLabel(Path(path).name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 9pt;")
        name_label.setToolTip(path)
        layout.addWidget(name_label)

        viewer = ImageViewer()
        viewer.show_image(path)
        layout.addWidget(viewer, stretch=1)
        return pane

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
