from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image
from typing import List, Optional

# Thumbnails are rendered at this resolution so they stay sharp when the
# filmstrip is dragged wider; the list view scales them down for display.
THUMB_SOURCE_SIZE = 320

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".m4v", ".webm"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def is_video(path: str) -> bool:
    from pathlib import Path
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def load_video_frame(path: str, max_size: Optional[int] = None) -> Optional[QImage]:
    """Grab the first frame of a video as a QImage (or None on failure)."""
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        try:
            ok, frame = cap.read()
        finally:
            cap.release()
        if not ok or frame is None:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        qimage = QImage(frame.data, w, h, frame.strides[0], QImage.Format.Format_RGB888).copy()
        if max_size and (w > max_size or h > max_size):
            qimage = qimage.scaled(
                max_size, max_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return qimage
    except Exception:
        return None


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
                if is_video(path):
                    pixmap = self._load_video_thumbnail(path)
                else:
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

    def _load_video_thumbnail(self, path: str) -> QPixmap | None:
        qimage = load_video_frame(path, max_size=self._size)
        if qimage is None:
            return None
        return QPixmap.fromImage(qimage)

    def cancel(self) -> None:
        self._cancelled = True
