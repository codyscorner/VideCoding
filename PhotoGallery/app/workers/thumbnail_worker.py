from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image
from typing import List

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}


class ThumbnailWorker(QThread):
    thumbnail_ready = pyqtSignal(int, QPixmap)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, image_paths: List[str], thumbnail_size: int = 120, parent=None):
        super().__init__(parent)
        self._paths = image_paths
        self._size = thumbnail_size
        self._cancelled = False

    def run(self) -> None:
        try:
            for i, path in enumerate(self._paths):
                if self._cancelled:
                    return
                pixmap = self._load_thumbnail(path)
                if pixmap is not None and not pixmap.isNull():
                    self.thumbnail_ready.emit(i, pixmap)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _load_thumbnail(self, path: str) -> QPixmap | None:
        try:
            with Image.open(path) as img:
                img.thumbnail((self._size, self._size), Image.LANCZOS)
                img = img.convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
                return QPixmap.fromImage(qimage)
        except Exception:
            return None

    def cancel(self) -> None:
        self._cancelled = True
