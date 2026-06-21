import sys
import multiprocessing
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

VERSION = "1.1.0"


def get_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Gallery")
    app.setApplicationVersion(VERSION)

    script_dir = get_script_dir()
    icon_path = script_dir / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from config import ConfigManager
    from app.ui.main_window import MainWindow

    config_file = script_dir / "photo_gallery_config.json"
    config_manager = ConfigManager(config_file)

    window = MainWindow(config_manager, VERSION)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
