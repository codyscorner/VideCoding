from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

from config import ConfigManager
from ui.settings_dialog import SettingsDialog
from ui.prompt_tab import PromptTab
from ui.styles import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, version: str):
        super().__init__()
        self._config = config
        self.setWindowTitle(f"Prompt Enhancer v{version}")
        self.setStyleSheet(STYLESHEET)
        self.resize(920, 780)

        self._build_menu()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        header = QLabel("✨ Prompt Enhancer")
        header.setObjectName("header")
        layout.addWidget(header)

        self._prompt_tab = PromptTab(config)
        layout.addWidget(self._prompt_tab, stretch=1)

        self.setCentralWidget(central)

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        settings_action = file_menu.addAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

    def _open_settings(self):
        dlg = SettingsDialog(self._config, self)
        if dlg.exec():
            self._prompt_tab.refresh_mode()
