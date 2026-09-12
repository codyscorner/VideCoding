"""
ComfyUI Video Creator
Version: 2.1.0

Single-shot ComfyUI API workflow runner: pick an image (tab 1), a video to
extend (tab 2), or just write a prompt (tab 3, text → video), pick a
workflow JSON, run it on local ComfyUI or RunPod, and download the finished
video to a local folder.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from config import CONFIG_NAME, ConfigManager, app_dir
from ui.main_window import MainWindow

VERSION = "2.1.0"

# Windows taskbar icon fix — must run before QApplication is created
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ComfyUI.VideoCreator.1")
except Exception:
    pass


def _force_foreground(window):
    """raise_()/activateWindow() alone often get silently ignored - Windows
    blocks a background process from stealing focus unless it looks like the
    user just pressed a key. A harmless Alt tap satisfies that check so a
    Stream-Deck-launched (or otherwise unfocused-parent) start actually comes
    to the front instead of just flashing in the taskbar."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = int(window.winId())
        user32.keybd_event(0x12, 0, 0, 0)   # VK_MENU (Alt) down
        user32.keybd_event(0x12, 0, 2, 0)   # VK_MENU up (KEYEVENTF_KEYUP)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    window.raise_()
    window.activateWindow()


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
    _force_foreground(window)
    QTimer.singleShot(200, lambda: _force_foreground(window))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
