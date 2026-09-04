"""
ComfyUI Workflow Editor
Version: 1.2.0
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

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

    # Bring the window to the front on startup so it isn't buried behind other
    # windows. Done now and again once the event loop is running, because Windows
    # can ignore the first activateWindow() when another app has the foreground.
    # One-time only — the window is not kept always-on-top.
    window.bring_to_front()
    QTimer.singleShot(150, window.bring_to_front)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
