from __future__ import annotations

import json
import sys
from pathlib import Path


DEFAULT_CONFIG: dict = {
    "snapshot_sources": [],
    "destination": "",
    "retention_days": 365,
    "robocopy_threads": 16,
    "versioned_files": True,
}


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        name = Path(sys.executable).stem
    else:
        base = Path(__file__).parent
        name = Path(__file__).stem.replace("config", "NAS_Backup")
    return base / f"{name}_config.json"


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_config_path()
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    saved = json.load(fh)
                return {**DEFAULT_CONFIG, **saved}
            except (json.JSONDecodeError, OSError):
                pass
        # Write defaults on first run
        self.save_data(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save_data(self, data: dict) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=4)
        except OSError:
            pass

    def save(self) -> None:
        self.save_data(self._data)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def update(self, values: dict) -> None:
        self._data.update(values)

    def get_all(self) -> dict:
        return dict(self._data)
