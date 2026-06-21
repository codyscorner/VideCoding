from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QTransform


class ImageViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_pixmap: QPixmap | None = None
        self._rotation: int = 0  # degrees: 0, 90, 180, 270
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setObjectName("image_viewer")
        self.setText("No image selected")

    def show_image(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.setText(f"Cannot load image")
            self._current_pixmap = None
        else:
            self._current_pixmap = pixmap
            self._rotation = 0
            self._update_scaled()

    def rotate(self, degrees: int) -> None:
        if self._current_pixmap is None:
            return
        self._rotation = (self._rotation + degrees) % 360
        self._update_scaled()

    def clear_image(self) -> None:
        self._current_pixmap = None
        self._rotation = 0
        self.clear()
        self.setText("No image selected")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_pixmap:
            self._update_scaled()

    def _update_scaled(self) -> None:
        if self._current_pixmap:
            pixmap = self._current_pixmap
            if self._rotation != 0:
                pixmap = pixmap.transformed(
                    QTransform().rotate(self._rotation),
                    Qt.TransformationMode.SmoothTransformation,
                )
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)
