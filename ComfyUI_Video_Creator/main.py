"""
ComfyUI Video Creator
Version: 1.3.5

Single-shot ComfyUI API workflow runner: pick an image (tab 1) or a video
to extend (tab 2), pick a workflow JSON, run it on local ComfyUI or RunPod,
and download the finished video to a local folder.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config import CONFIG_NAME, ConfigManager, app_dir
from ui.main_window import MainWindow

VERSION = "1.3.7"

# Windows taskbar icon fix — must run before QApplication is created
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ComfyUI.VideoCreator.1")
except Exception:
    pass


def _find_icon() -> Path | None:
    candidate = app_dir() / "app_icon.ico"
    if candidate.exists():
        return candidate
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "app_icon.ico"
        if bundled.exists():
            return bundled
    return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ComfyUI Video Creator")

    icon = _find_icon()
    if icon:
        app.setWindowIcon(QIcon(str(icon)))

    base = app_dir()
    config = ConfigManager(base / CONFIG_NAME)
    config.set("_base_dir", str(base))

    window = MainWindow(config, VERSION)
    window.show()
    window.raise_()
    window.activateWindow()
    QTimer.singleShot(200, lambda: (window.raise_(), window.activateWindow()))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
