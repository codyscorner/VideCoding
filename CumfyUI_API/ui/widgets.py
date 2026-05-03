from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QImage

from ui.styles import COLORS

THUMB_SIZE = 200


class ThumbnailGrid(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 12, THUMB_SIZE + 12))
        self.setSpacing(4)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWrapping(True)
        self.setWordWrap(False)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px;"
            f" padding-right: 16px; }}"
            f"QListWidget::item {{ border: 2px solid transparent; border-radius: 4px; }}"
            f"QListWidget::item:selected {{ background-color: transparent;"
            f" border: 2px solid {COLORS['accent']}; border-radius: 4px; }}"
        )

    def clear_grid(self):
        self.clear()

    def add_item(self, img: QImage, key: str, label: str):
        pix = QPixmap.fromImage(img)
        canvas = QPixmap(THUMB_SIZE, THUMB_SIZE)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        x = (THUMB_SIZE - pix.width()) // 2
        y = (THUMB_SIZE - pix.height()) // 2
        painter.drawPixmap(x, y, pix)
        painter.end()
        item = QListWidgetItem(QIcon(canvas), label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.addItem(item)

    def selected_key(self) -> str | None:
        items = self.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def select_key(self, key: str):
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self.setCurrentItem(item)
                self.scrollToItem(item)
                return
