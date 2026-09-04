"""
FaceFinder - Main Entry Point
Version: 1.4.2
"""

import sys
from multiprocessing import freeze_support
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from config import ConfigManager
from ui.main_window import MainWindow

VERSION = "1.4.2"


def get_script_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FaceFinder")

    script_dir = get_script_dir()
    icon_path = script_dir / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config_file = script_dir / "main_config.json"
    config_manager = ConfigManager(config_file)

    window = MainWindow(config_manager, VERSION)
    window.show()

    # Close the PyInstaller splash screen once the main window is up
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    # Bring the window to the front on startup so it isn't buried
    # behind other windows (one-time — not always-on-top)
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    freeze_support()
    main()
