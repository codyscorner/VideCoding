import os
import base64
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from ui.file_list_panel import FileListPanel
from ui.video_player_panel import VideoPlayerPanel
from core.settings import AppSettings
from version import VERSION

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "settings.json")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Desktop Video Browser v{VERSION}")
        self.resize(1200, 700)
        icon_path = Path(__file__).parent.parent.parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.file_list_panel = FileListPanel()
        self.video_player_panel = VideoPlayerPanel()

        self.file_list_panel.fileSelected.connect(self.video_player_panel.load_video)
        self.file_list_panel.folderOpened.connect(self._on_folder_opened)
        self.video_player_panel.navigateRequested.connect(self.file_list_panel.navigate)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.file_list_panel)
        self.splitter.addWidget(self.video_player_panel)
        self.splitter.setSizes([360, 840])

        self.setCentralWidget(self.splitter)
        self._load_settings()

    def _load_settings(self):
        self.settings = AppSettings.load(SETTINGS_PATH)

        if self.settings.geometry:
            self.restoreGeometry(base64.b64decode(self.settings.geometry))

        if self.settings.last_opened_folder and os.path.isdir(self.settings.last_opened_folder):
            self.file_list_panel.load_folder(self.settings.last_opened_folder)

    def _on_folder_opened(self, folder: str):
        self.video_player_panel.release()
        self.settings.last_opened_folder = folder

    def closeEvent(self, event):
        self.settings.geometry = base64.b64encode(self.saveGeometry().data()).decode("ascii")
        self.settings.save(SETTINGS_PATH)
        super().closeEvent(event)
