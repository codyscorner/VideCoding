from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QFileSystemModel
from PySide6.QtCore import Signal, QDir, Qt

_NAV_KEYS = {
    Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
    Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown,
    Qt.Key_Return, Qt.Key_Enter,
}


class _NavigableTreeView(QTreeView):
    """QTreeView that reports its current index only after a real key press.

    QFileSystemModel/QTreeView can change the "current" index on their own
    (e.g. defaulting to the process's working-directory drive once the drive
    list finishes populating), which would otherwise be indistinguishable
    from a genuine user selection via currentChanged.
    """

    def __init__(self, on_navigate):
        super().__init__()
        self._on_navigate = on_navigate

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        if event.key() in _NAV_KEYS:
            self._on_navigate(self.currentIndex())


class FolderTreePanel(QWidget):
    folderSelected = Signal(str)

    def __init__(self):
        super().__init__()
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Drives)

        self.tree = _NavigableTreeView(self._emit_for_index)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(""))
        self.tree.setHeaderHidden(True)
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.setAnimated(True)
        self.tree.clicked.connect(self._emit_for_index)
        layout.addWidget(self.tree)

    def _emit_for_index(self, index) -> None:
        if self._syncing or not index.isValid():
            return
        path = self.model.filePath(index)
        if path:
            self.folderSelected.emit(path)

    def set_current_folder(self, path: str) -> None:
        if not path:
            return
        index = self.model.index(path)
        if not index.isValid():
            return

        self._syncing = True
        try:
            parent = index.parent()
            while parent.isValid():
                self.tree.expand(parent)
                parent = parent.parent()
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)
        finally:
            self._syncing = False
