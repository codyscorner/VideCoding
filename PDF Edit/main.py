"""PDF Edit — desktop PDF markup and page management.

Entry point. See PLAN.md for architecture and PROJECT_SUMMARY.md for status.
"""

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from theme import DARK_GREEN_QSS
from ui.main_window import MainWindow

APP_NAME = "PDF Edit"
APP_VERSION = "1.1.0"


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DARK_GREEN_QSS)
    icon_path = resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow(APP_NAME, APP_VERSION)
    win.show()

    # allow "pdfedit.exe file.pdf" / drag-onto-exe opening
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        win.open_path(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
