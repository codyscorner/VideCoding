import os
import sys


def get_app_dir() -> str:
    """Directory the app's persistent files (settings.json) should live in.

    This is the EXE's own folder when frozen by PyInstaller, so the app stays
    portable. In dev mode it's the project root.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts: str) -> str:
    """Path to a bundled read-only resource (icon, stylesheet).

    PyInstaller onefile builds extract data files to a temp dir (sys._MEIPASS)
    at runtime, which is where __file__-based lookups break.
    """
    base = getattr(sys, "_MEIPASS", get_app_dir())
    return os.path.join(base, *parts)
