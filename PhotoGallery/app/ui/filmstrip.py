from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QPen
from typing import List, Optional

MIN_DISPLAY_SIZE = 64
MAX_DISPLAY_SIZE = 320  # keep in sync with THUMB_SOURCE_SIZE (source render resolution)


class FilmStrip(QListWidget):
    image_selected = pyqtSignal(int)

    def __init__(self, thumbnail_size: int = 120, parent=None):
        super().__init__(parent)
        self.thumbnail_size = max(MIN_DISPLAY_SIZE, min(MAX_DISPLAY_SIZE, thumbnail_size))
        self._base_pixmaps: List[Optional[QPixmap]] = []
        self._badges: List[dict] = []  # per-index: rating, flagged, is_video
        self._setup_view()
        self.itemClicked.connect(self._on_item_clicked)

    def _setup_view(self) -> None:
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setIconSize(QSize(self.thumbnail_size, self.thumbnail_size))
        self.setMinimumWidth(MIN_DISPLAY_SIZE + 14)
        self.setMaximumWidth(MAX_DISPLAY_SIZE + 20)
        self.setSpacing(1)
        self.setResizeMode(QListWidget.ResizeMode.Fixed)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setUniformItemSizes(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        size = max(MIN_DISPLAY_SIZE, min(MAX_DISPLAY_SIZE, self.viewport().width() - 8))
        self._apply_display_size(size)

    def _apply_display_size(self, size: int) -> None:
        if size == self.thumbnail_size:
            return
        self.thumbnail_size = size
        self.setIconSize(QSize(size, size))
        hint = QSize(size + 6, size + 4)
        for i in range(self.count()):
            self.item(i).setSizeHint(hint)

    def populate(self, image_paths: List[str]) -> None:
        self.clear()
        self._base_pixmaps = [None] * len(image_paths)
        self._badges = [
            {"rating": 0, "flagged": False, "is_video": False}
            for _ in image_paths
        ]
        placeholder = QPixmap(self.thumbnail_size, self.thumbnail_size)
        placeholder.fill(Qt.GlobalColor.darkGray)
        placeholder_icon = QIcon(placeholder)
        for path in image_paths:
            item = QListWidgetItem()
            item.setIcon(placeholder_icon)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setSizeHint(QSize(self.thumbnail_size + 6, self.thumbnail_size + 4))
            self.addItem(item)

    def set_thumbnail(self, index: int, pixmap: QPixmap) -> None:
        if 0 <= index < len(self._base_pixmaps):
            self._base_pixmaps[index] = pixmap
            self._refresh_icon(index)

    def set_badges(self, index: int, rating: int, flagged: bool, is_video: bool) -> None:
        if 0 <= index < len(self._badges):
            self._badges[index] = {
                "rating": rating, "flagged": flagged, "is_video": is_video,
            }
            self._refresh_icon(index)

    def _refresh_icon(self, index: int) -> None:
        item = self.item(index)
        base = self._base_pixmaps[index] if index < len(self._base_pixmaps) else None
        if item is None or base is None:
            return
        badges = self._badges[index]
        if not (badges["rating"] or badges["flagged"] or badges["is_video"]):
            item.setIcon(QIcon(base))
            return
        composed = QPixmap(base)
        painter = QPainter(composed)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Badges are painted on the source-resolution pixmap, so scale them to
        # the pixmap rather than the on-screen display size.
        base_dim = max(composed.width(), composed.height())
        font = QFont("Segoe UI Emoji", max(8, base_dim // 12))
        painter.setFont(font)

        if badges["is_video"]:
            # ▶ badge, bottom-left
            r = base_dim // 6
            circle = QRectF(3, composed.height() - r * 2 - 3, r * 2, r * 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 170))
            painter.drawEllipse(circle)
            painter.setPen(QPen(QColor("white")))
            painter.drawText(circle, Qt.AlignmentFlag.AlignCenter, "▶")

        top_text = ""
        if badges["flagged"]:
            top_text += "⚑ "
        if badges["rating"]:
            top_text += "★" * badges["rating"]
        if top_text:
            metrics = painter.fontMetrics()
            w = metrics.horizontalAdvance(top_text) + 8
            h = metrics.height() + 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 170))
            painter.drawRect(0, 0, w, h)
            painter.setPen(QPen(QColor("#facc15")))
            painter.drawText(QRectF(4, 1, w - 4, h), Qt.AlignmentFlag.AlignVCenter, top_text)

        painter.end()
        item.setIcon(QIcon(composed))

    def remove_index(self, index: int) -> None:
        if 0 <= index < self.count():
            self.takeItem(index)
            if index < len(self._base_pixmaps):
                self._base_pixmaps.pop(index)
            if index < len(self._badges):
                self._badges.pop(index)

    def select_index(self, index: int) -> None:
        item = self.item(index)
        if item:
            self.setCurrentItem(item)
            self.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            # Prev/next image is the main window's job, even when the list has focus.
            event.ignore()
        elif key == Qt.Key.Key_Space:
            if self.currentRow() >= 0:
                self.image_selected.emit(self.currentRow())
        else:
            # Up/Down keep native behavior: move the highlight without loading.
            super().keyPressEvent(event)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.image_selected.emit(self.row(item))
