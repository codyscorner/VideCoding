import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config import ConfigManager
from ui.main_window import MainWindow
from ui.styles import STYLESHEET

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
VERSION = "1.0.0"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("FolderSync")
    app.setStyleSheet(STYLESHEET)

    icon_path = BASE_DIR / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config = ConfigManager(BASE_DIR / "foldersync_config.json")
    window = MainWindow(config, BASE_DIR, VERSION)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
