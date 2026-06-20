import json
from pathlib import Path
from typing import Any


class ConfigManager:
    DEFAULT = {
        "mode": "local",
        "comfyui_url": "http://127.0.0.1:8000",
        "runpod_url": "",
        "input_dir": "",
        "output_dir": "",
        "workflow_path": "",
        "prompts_file": "",
        "skip_existing": True,
    }

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data = self._load()

    def _load(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**self.DEFAULT, **json.load(f)}
            except (json.JSONDecodeError, OSError):
                pass
        return self.DEFAULT.copy()

    def save(self) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_all(self) -> dict:
        return self._data.copy()
