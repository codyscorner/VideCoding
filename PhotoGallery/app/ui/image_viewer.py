from PyQt6.QtWidgets import QLabel, QSizePolicy, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform


class ImageViewer(QLabel):
    crop_selected = pyqtSignal(QRect)   # rect in rotated-image coordinates
    activated = pyqtSignal()            # double-click on the viewer

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_pixmap: QPixmap | None = None
        self._rotation: int = 0  # degrees clockwise: 0, 90, 180, 270
        self._crop_mode: bool = False
        self._rubber_band: QRubberBand | None = None
        self._band_origin: QPoint | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setObjectName("image_viewer")
        self.setText("No image selected")

    @property
    def rotation(self) -> int:
        return self._rotation

    @property
    def has_image(self) -> bool:
        return self._current_pixmap is not None

    def show_image(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.setText("Cannot load image")
            self._current_pixmap = None
        else:
            self._current_pixmap = pixmap
            self._rotation = 0
            self._update_scaled()

    def show_pixmap(self, pixmap: QPixmap) -> None:
        """Display an already-loaded pixmap (e.g. a video's first frame)."""
        if pixmap.isNull():
            self.clear_image()
            return
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
        self.set_crop_mode(False)
        self.clear()
        self.setText("No image selected")

    # ── Crop mode ─────────────────────────────────────────────────────────────

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled and self._current_pixmap is not None
        self.setCursor(
            Qt.CursorShape.CrossCursor if self._crop_mode
            else Qt.CursorShape.ArrowCursor
        )
        if not self._crop_mode and self._rubber_band:
            self._rubber_band.hide()

    def mousePressEvent(self, event) -> None:
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton:
            self._band_origin = event.position().toPoint()
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._band_origin, QSize()))
            self._rubber_band.show()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._crop_mode and self._band_origin is not None:
            self._rubber_band.setGeometry(
                QRect(self._band_origin, event.position().toPoint()).normalized()
            )
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._crop_mode and self._band_origin is not None:
            band_rect = self._rubber_band.geometry()
            self._band_origin = None
            image_rect = self._map_to_image(band_rect)
            if image_rect is not None and image_rect.width() > 2 and image_rect.height() > 2:
                self.crop_selected.emit(image_rect)
            else:
                self._rubber_band.hide()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.activated.emit()
        super().mouseDoubleClickEvent(event)

    def _rotated_pixmap(self) -> QPixmap | None:
        if self._current_pixmap is None:
            return None
        if self._rotation == 0:
            return self._current_pixmap
        return self._current_pixmap.transformed(
            QTransform().rotate(self._rotation),
            Qt.TransformationMode.SmoothTransformation,
        )

    def _map_to_image(self, label_rect: QRect) -> QRect | None:
        """Map a rect in label coordinates to rotated-image coordinates."""
        rotated = self._rotated_pixmap()
        displayed = self.pixmap()
        if rotated is None or displayed is None or displayed.isNull():
            return None
        # Displayed pixmap is centered in the label
        offset_x = (self.width() - displayed.width()) // 2
        offset_y = (self.height() - displayed.height()) // 2
        display_rect = QRect(offset_x, offset_y, displayed.width(), displayed.height())
        clipped = label_rect.intersected(display_rect)
        if clipped.isEmpty():
            return None
        scale = rotated.width() / displayed.width()
        return QRect(
            round((clipped.x() - offset_x) * scale),
            round((clipped.y() - offset_y) * scale),
            round(clipped.width() * scale),
            round(clipped.height() * scale),
        ).intersected(QRect(0, 0, rotated.width(), rotated.height()))

    # ── Painting ──────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_pixmap:
            self._update_scaled()

    def _update_scaled(self) -> None:
        pixmap = self._rotated_pixmap()
        if pixmap:
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)
