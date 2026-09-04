"""
ComfyUI Workflow Editor
Version: 1.2.0
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow
from settings import Settings

VERSION = "1.2.0"


def get_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ComfyUI Workflow Editor")

    script_dir = get_script_dir()
    icon_path = script_dir / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    settings = Settings(script_dir)
    window = MainWindow(VERSION, settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
