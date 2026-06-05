"""
ComfyUI Workflow Chain Automator
Version: 3.1.0
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from config import ConfigManager
from ui.main_window import MainWindow

VERSION = "3.1.0"

# Windows taskbar icon fix — must be called before QApplication
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "ComfyUI.ChainAutomator.2"
    )
except Exception:
    pass


def get_script_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _find_icon() -> Path | None:
    """Look for app_icon.ico next to the EXE, then in the bundled _MEIPASS dir."""
    script_dir = get_script_dir()
    candidate = script_dir / "app_icon.ico"
    if candidate.exists():
        return candidate
    if getattr(sys, 'frozen', False):
        bundled = Path(sys._MEIPASS) / "app_icon.ico"
        if bundled.exists():
            return bundled
    return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ComfyUI Workflow Chain Automator")

    icon_path = _find_icon()
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))

    script_dir = get_script_dir()

    config_file = script_dir / "main_config.json"
    config_manager = ConfigManager(config_file)
    config_manager.set("_base_dir", str(script_dir))

    window = MainWindow(config_manager, VERSION)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
