from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon
from typing import List


class FilmStrip(QListWidget):
    image_selected = pyqtSignal(int)

    def __init__(self, thumbnail_size: int = 120, parent=None):
        super().__init__(parent)
        self.thumbnail_size = thumbnail_size
        self._setup_view()
        self.itemClicked.connect(self._on_item_clicked)

    def _setup_view(self) -> None:
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setIconSize(QSize(self.thumbnail_size, self.thumbnail_size))
        self.setFixedWidth(self.thumbnail_size + 14)
        self.setSpacing(1)
        self.setResizeMode(QListWidget.ResizeMode.Fixed)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setUniformItemSizes(True)

    def populate(self, image_paths: List[str]) -> None:
        self.clear()
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
        item = self.item(index)
        if item:
            item.setIcon(QIcon(pixmap))

    def select_index(self, index: int) -> None:
        item = self.item(index)
        if item:
            self.setCurrentItem(item)
            self.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.image_selected.emit(self.row(item))
