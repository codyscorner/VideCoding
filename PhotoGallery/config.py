import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "last_folder": "",
    "slideshow_delay": 5.0,
    "fade_duration": 2.0,
    "thumbnail_size": 120,
    "filmstrip_width": 134,
    "window_width": 1200,
    "window_height": 750,
    "include_subfolders": False,
}


class ConfigManager:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config: dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.config = {**DEFAULT_CONFIG, **saved}
            except (json.JSONDecodeError, IOError):
                self.config = DEFAULT_CONFIG.copy()

    def save(self) -> None:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Config save error: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
