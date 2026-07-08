"""Configuration management for Bulk File Randomizer"""

import json
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    DEFAULT_CONFIG: Dict[str, Any] = {
        "last_source_folder": "",
        "last_prefix": "",
        "last_file_mask": "*.*",
        "recursive_search": False,
        "last_mode": "copy",
    }

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            except (json.JSONDecodeError, OSError):
                pass
        return self.DEFAULT_CONFIG.copy()

    def save(self) -> bool:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self._config, f, indent=4)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
