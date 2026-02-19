"""Grid view widget for displaying image thumbnails"""

from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage, QKeyEvent
from typing import List, Optional, Dict
from PIL import Image
import io

from app.core.image_utils import ImageUtils


class ThumbnailView(QListWidget):
    """Grid view widget for image thumbnails"""

    # Signals
    image_selected = Signal(str)  # path
    image_double_clicked = Signal(str)  # path - open compare dialog
    selection_changed = Signal(list)  # List of selected paths
    delete_requested = Signal()  # Delete key pressed

    def __init__(self, thumbnail_size: int = 150, parent=None):
        """
        Initialize thumbnail view

        Args:
            thumbnail_size: Size of thumbnails in pixels
            parent: Parent widget
        """
        super().__init__(parent)
        self.thumbnail_size = thumbnail_size
        self._thumbnails: Dict[str, QPixmap] = {}  # Cache
        self._path_map: Dict[int, str] = {}  # item row -> path

        self._setup_view()
        self._connect_signals()

    def _setup_view(self) -> None:
        """Configure as icon grid"""
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(self.thumbnail_size, self.thumbnail_size))
        self.setSpacing(10)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)

        # Set item size to accommodate thumbnail + text (filename + similarity %)
        self.setGridSize(QSize(
            self.thumbnail_size + 20,
            self.thumbnail_size + 75
        ))

    def _connect_signals(self) -> None:
        """Connect internal signals"""
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemClicked.connect(self._on_item_clicked)

    def set_images(
        self,
        image_paths: List[str],
        similarities: Optional[Dict[str, float]] = None,
        representative: Optional[str] = None
    ) -> None:
        """
        Display images in the grid

        Args:
            image_paths: List of image paths to display
            similarities: Optional dict mapping path to similarity score
            representative: Optional path to highlight as representative
        """
        self.clear()
        self._path_map.clear()

        for i, path in enumerate(image_paths):
            # Create thumbnail
            pixmap = self._get_thumbnail(path)

            # Create item
            item = QListWidgetItem()

            # Set icon
            if pixmap:
                item.setIcon(QIcon(pixmap))
            else:
                # Placeholder for failed thumbnails
                item.setIcon(QIcon())

            # Set text (filename + optional similarity)
            # Scale max filename length to thumbnail width (~1 char per 4px)
            max_chars = max(20, (self.thumbnail_size + 20) // 4 * 2)
            filename = path.split('\\')[-1].split('/')[-1]
            if len(filename) > max_chars:
                filename = filename[:max_chars - 3] + "..."

            if similarities and path in similarities:
                score = similarities[path]
                item.setText(f"{filename}\n{score:.1%}")
            else:
                item.setText(filename)

            # Store path in item data
            item.setData(Qt.ItemDataRole.UserRole, path)

            # Highlight representative
            if representative and path == representative:
                item.setBackground(Qt.GlobalColor.darkGreen)

            self.addItem(item)
            self._path_map[i] = path

    def _get_thumbnail(self, path: str) -> Optional[QPixmap]:
        """
        Get or create thumbnail for image

        Args:
            path: Path to image file

        Returns:
            QPixmap or None if failed
        """
        # Check cache
        if path in self._thumbnails:
            return self._thumbnails[path]

        # Create thumbnail
        pil_thumb = ImageUtils.create_thumbnail(
            path,
            size=(self.thumbnail_size, self.thumbnail_size)
        )

        if pil_thumb is None:
            return None

        # Convert PIL Image to QPixmap
        pixmap = self._pil_to_pixmap(pil_thumb)

        # Cache and return
        if pixmap:
            self._thumbnails[path] = pixmap

        return pixmap

    def _pil_to_pixmap(self, pil_image: Image.Image) -> Optional[QPixmap]:
        """
        Convert PIL Image to QPixmap

        Args:
            pil_image: PIL Image object

        Returns:
            QPixmap or None on failure
        """
        try:
            # Convert to bytes
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            buffer.seek(0)

            # Create QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())

            return pixmap
        except Exception:
            return None

    def get_selected_paths(self) -> List[str]:
        """
        Get paths of selected images

        Returns:
            List of selected image paths
        """
        paths = []
        for item in self.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        return paths

    def clear_thumbnails(self) -> None:
        """Clear thumbnail cache and view"""
        self._thumbnails.clear()
        self._path_map.clear()
        self.clear()

    def highlight_items(self, paths: List[str], color: Qt.GlobalColor) -> None:
        """
        Highlight specific items with a color

        Args:
            paths: List of paths to highlight
            color: Background color to use
        """
        paths_set = set(paths)
        for i in range(self.count()):
            item = self.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in paths_set:
                item.setBackground(color)

    def _on_selection_changed(self) -> None:
        """Handle selection change"""
        paths = self.get_selected_paths()
        self.selection_changed.emit(paths)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.image_selected.emit(path)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle item double-click"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.image_double_clicked.emit(path)

    def set_thumbnail_size(self, size: int) -> None:
        """
        Update thumbnail size

        Args:
            size: New thumbnail size in pixels
        """
        self.thumbnail_size = size
        self.setIconSize(QSize(size, size))
        self.setGridSize(QSize(size + 20, size + 75))

        # Clear cache to regenerate at new size
        self._thumbnails.clear()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events"""
        if event.key() == Qt.Key.Key_Delete:
            if self.selectedItems():
                self.delete_requested.emit()
        else:
            super().keyPressEvent(event)
