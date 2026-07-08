"""Thin wrapper over QSettings for persisted preferences.

Phase 2 uses this to remember the last opened folder, the recursive toggle, and
volume. Full playlist persistence lands in Phase 5.
"""

from __future__ import annotations

from PyQt6.QtCore import QSettings

_ORG = "VibeCoded"
_APP = "Music Player"


def _settings() -> QSettings:
    return QSettings(_ORG, _APP)


def get_last_folder() -> str:
    return str(_settings().value("last_folder", "", type=str))


def set_last_folder(path: str) -> None:
    _settings().setValue("last_folder", path)


def get_recursive() -> bool:
    return bool(_settings().value("recursive", True, type=bool))


def set_recursive(value: bool) -> None:
    _settings().setValue("recursive", value)


def get_volume() -> int:
    return int(_settings().value("volume", 80, type=int))


def set_volume(value: int) -> None:
    _settings().setValue("volume", value)


def get_repeat_mode() -> str:
    mode = str(_settings().value("repeat_mode", "off", type=str))
    return mode if mode in ("off", "all", "one") else "off"


def set_repeat_mode(value: str) -> None:
    _settings().setValue("repeat_mode", value)


def get_shuffle() -> bool:
    return bool(_settings().value("shuffle", False, type=bool))


def set_shuffle(value: bool) -> None:
    _settings().setValue("shuffle", value)


def get_library_root() -> str:
    return str(_settings().value("library_root", "", type=str))


def set_library_root(path: str) -> None:
    _settings().setValue("library_root", path)
