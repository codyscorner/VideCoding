import json
from pathlib import Path


class Settings:
    def __init__(self, base_dir: Path):
        self._path = base_dir / "workflow_editor_config.json"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self._save()
