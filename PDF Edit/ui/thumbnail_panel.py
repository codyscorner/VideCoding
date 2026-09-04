"""Thumbnail sidebar: async rendering, drag reorder, external PDF drops.

Thumbnails are rendered in a worker thread from an independent document
copy (opened from bytes), so the UI thread's fitz document is never touched
off-thread.
"""

import fitz
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QMenu

THUMB_WIDTH = 130


class _ThumbWorker(QThread):
    thumbReady = pyqtSignal(int, QImage)

    def __init__(self, data: bytes, indices: list[int], parent=None):
        super().__init__(parent)
        self._data = data
        self._indices = indices

    def run(self):
        try:
            doc = fitz.open("pdf", self._data)
        except Exception:
            return
        try:
            for i in self._indices:
                if self.isInterruptionRequested():
                    return
                if i >= doc.page_count:
                    continue
                page = doc[i]
                zoom = THUMB_WIDTH / max(1.0, page.rect.width)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                      alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                             QImage.Format.Format_RGB888).copy()
                self.thumbReady.emit(i, img)
        finally:
            doc.close()


class ThumbnailPanel(QListWidget):
    pagesReordered = pyqtSignal(list)   # new order as list of old indices
    pdfDropped = pyqtSignal(list)       # list of file paths to insert
    pageAction = pyqtSignal(str, int)   # "delete"|"rotate_l"|"rotate_r"|"duplicate", pno

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(THUMB_WIDTH, int(THUMB_WIDTH * 1.35)))
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.setMinimumWidth(THUMB_WIDTH + 60)
        self.setMaximumWidth(THUMB_WIDTH + 110)
        self._worker: _ThumbWorker | None = None
        self._suppress_reorder = False

    # ------------------------------------------------------------- populate

    def populate(self, data: bytes | None, page_count: int,
                 current: int = 0):
        """Rebuild the whole list and re-render every thumbnail."""
        self._stop_worker()
        self._suppress_reorder = True
        self.clear()
        placeholder = QPixmap(THUMB_WIDTH, int(THUMB_WIDTH * 1.35))
        placeholder.fill(Qt.GlobalColor.darkGray)
        for i in range(page_count):
            item = QListWidgetItem(QIcon(placeholder), f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.addItem(item)
        self._suppress_reorder = False
        if page_count:
            self.setCurrentRow(min(current, page_count - 1))
        if data and page_count:
            self._start_worker(data, list(range(page_count)))

    def refresh_pages(self, data: bytes, indices: list[int]):
        """Re-render specific thumbnails (e.g. after annotating a page)."""
        self._start_worker(data, indices)

    def _start_worker(self, data: bytes, indices: list[int]):
        self._stop_worker()
        self._worker = _ThumbWorker(data, indices, self)
        self._worker.thumbReady.connect(self._on_thumb)
        self._worker.start()

    def _stop_worker(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(3000)
            self._worker = None

    def _on_thumb(self, index: int, img: QImage):
        if 0 <= index < self.count():
            self.item(index).setIcon(QIcon(QPixmap.fromImage(img)))

    # ------------------------------------------------------------- reorder

    def dropEvent(self, ev):
        if ev.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in ev.mimeData().urls()
                     if u.toLocalFile().lower().endswith(".pdf")]
            if paths:
                ev.acceptProposedAction()
                self.pdfDropped.emit(paths)
            return
        before = [self.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self.count())]
        super().dropEvent(ev)
        after = [self.item(i).data(Qt.ItemDataRole.UserRole)
                 for i in range(self.count())]
        if not self._suppress_reorder and after != before:
            self.pagesReordered.emit(after)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
        else:
            super().dragEnterEvent(ev)

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
        else:
            super().dragMoveEvent(ev)

    # ------------------------------------------------------------- menu

    def _context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        row = self.row(item)
        menu = QMenu(self)
        actions = {
            menu.addAction("Rotate Left"): "rotate_l",
            menu.addAction("Rotate Right"): "rotate_r",
            menu.addAction("Duplicate Page"): "duplicate",
            menu.addAction("Delete Page"): "delete",
        }
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen in actions:
            self.pageAction.emit(actions[chosen], row)
