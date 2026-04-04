import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QFileDialog, QLabel
from PySide6.QtCore import Signal, Qt
from core.file_loader import list_video_files


class FileListPanel(QWidget):
    fileSelected = Signal(str)
    folderOpened = Signal(str)

    def __init__(self):
        super().__init__()
        self._current_folder: str = ""
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        btn_row = QHBoxLayout()

        self.open_button = QPushButton("Open Folder...")
        self.open_button.clicked.connect(self._browse_folder)
        btn_row.addWidget(self.open_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_button)

        layout.addLayout(btn_row)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget)

        self.path_label = QLabel("No folder selected")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #888; font-size: 11px; padding: 2px;")
        layout.addWidget(self.path_label)

    def load_folder(self, path: str) -> None:
        self._current_folder = path
        self.path_label.setText(path)
        self.list_widget.clear()
        for full_path in list_video_files(path):
            item = QListWidgetItem(os.path.basename(full_path))
            item.setData(Qt.UserRole, full_path)
            self.list_widget.addItem(item)

    def _refresh(self) -> None:
        if self._current_folder:
            self.load_folder(self._current_folder)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self.load_folder(folder)
            self.folderOpened.emit(folder)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.fileSelected.emit(item.data(Qt.UserRole))

    def navigate(self, delta: int) -> None:
        count = self.list_widget.count()
        if count == 0:
            return
        current = self.list_widget.currentRow()
        new_row = max(0, min(count - 1, current + delta))
        if new_row != current:
            self.list_widget.setCurrentRow(new_row)

    def _on_row_changed(self, row: int) -> None:
        item = self.list_widget.item(row)
        if item:
            self.fileSelected.emit(item.data(Qt.UserRole))

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.load_folder(path)
                self.folderOpened.emit(path)
                break
