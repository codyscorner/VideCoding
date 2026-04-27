"""
ComfyUI Workflow Chain Automator
Version: 1.0.0
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from config import ConfigManager
from ui.main_window import MainWindow

VERSION = "1.0.0"


def get_script_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ComfyUI Chain Automator")

    script_dir = get_script_dir()
    icon_path = script_dir / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config_file = script_dir / "main_config.json"
    config_manager = ConfigManager(config_file)
    config_manager.set("_base_dir", str(script_dir))

    window = MainWindow(config_manager, VERSION)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
