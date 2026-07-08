"""Playlist table with drag-to-reorder.

Qt's built-in QTableWidget internal move is unreliable for whole-row moves, so
this subclass intercepts the drop, works out the source rows and target row, and
emits ``rowsMoved`` for the window to reorder the backing track list itself.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QTableWidget


class PlaylistTable(QTableWidget):
    rowsMoved = pyqtSignal(list, int)   # (source visual rows, target visual row)
    filesDropped = pyqtSignal(list)     # local file/folder paths from Explorer
    playPauseRequested = pyqtSignal()
    seekRelative = pyqtSignal(int)      # milliseconds (+/-)
    nextRequested = pyqtSignal()
    prevRequested = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        # DragDrop (not InternalMove) so rows can also be dragged out onto the
        # playlist sidebar; internal reorder is still handled in dropEvent.
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

    # ----------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        # External files/folders dragged in from Explorer.
        if event.mimeData().hasUrls():
            paths = [
                u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()
            ]
            if paths:
                self.filesDropped.emit(paths)
                event.acceptProposedAction()
                return
            event.ignore()
            return
        # Internal reorder.
        if event.source() is not self:
            event.ignore()
            return
        sources = sorted({idx.row() for idx in self.selectedIndexes()})
        if not sources:
            event.ignore()
            return
        target = self._drop_row(event)
        self.rowsMoved.emit(sources, target)
        event.accept()

    # ------------------------------------------------------------- keys
    def keyPressEvent(self, event) -> None:
        key = event.key()
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        if key == Qt.Key.Key_Space:
            self.playPauseRequested.emit()
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            idx = self.currentIndex()
            if idx.isValid():
                self.doubleClicked.emit(idx)  # reuse the play-on-activate path
            event.accept()
        elif key == Qt.Key.Key_Left and ctrl:
            self.prevRequested.emit()
            event.accept()
        elif key == Qt.Key.Key_Right and ctrl:
            self.nextRequested.emit()
            event.accept()
        elif key == Qt.Key.Key_Left:
            self.seekRelative.emit(-5000)
            event.accept()
        elif key == Qt.Key.Key_Right:
            self.seekRelative.emit(5000)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _drop_row(self, event) -> int:
        """Row index to insert before; rowCount() means append at the end."""
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        if not index.isValid():
            return self.rowCount()
        rect = self.visualRect(index)
        if pos.y() >= rect.center().y():
            return index.row() + 1
        return index.row()


class PlaylistSidebar(QListWidget):
    """Playlist list that accepts tracks dragged from the PlaylistTable.

    Emits ``tracksDropped`` with the playlist name the tracks were dropped on
    (the currently selected table rows are what get added).
    """

    tracksDropped = pyqtSignal(str)  # playlist name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def _from_table(self, event) -> bool:
        return isinstance(event.source(), PlaylistTable)

    def dragEnterEvent(self, event) -> None:
        if self._from_table(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        # only a named playlist (UserRole set) is a valid drop target
        name = item.data(Qt.ItemDataRole.UserRole) if item else None
        if self._from_table(event) and name:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        name = item.data(Qt.ItemDataRole.UserRole) if item else None
        if self._from_table(event) and name:
            self.tracksDropped.emit(name)
            event.acceptProposedAction()
        else:
            event.ignore()
