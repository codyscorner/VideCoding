import json
from pathlib import Path
from typing import Any


class ConfigManager:
    DEFAULT = {
        "anthropic_api_key": "",
        "gemini_api_key": "",
        "groq_api_key": "",
        "openrouter_api_key": "",
        "provider": "anthropic",
        "target_format": "WAN 2.2",
        "h3_mode": "I2VA",
        "last_model": {},
    }

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data = self._load()

    def _load(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return {**self.DEFAULT, **json.load(f)}
            except (json.JSONDecodeError, OSError):
                pass
        return self.DEFAULT.copy()

    def save(self) -> bool:
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
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

    def history_path(self) -> Path:
        base = Path(self.get("_base_dir", "."))
        return base / "prompt_history.json"
