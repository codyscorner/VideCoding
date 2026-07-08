"""Music Player — a folder-scanning playlist music player.

Entry point: builds the QApplication, applies the dark-blue theme, and shows
the main window.
"""

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import DARK_BLUE_QSS

__version__ = "1.0.0"
APP_NAME = "Music Player"
ORG_NAME = "VibeCoded"


def resource_path(*parts: str) -> str:
    """Resolve a bundled resource path (works from source and a PyInstaller EXE)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


ICON_PATH = resource_path("assets", "icon.ico")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)
    app.setStyleSheet(DARK_BLUE_QSS)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = MainWindow(version=__version__)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
