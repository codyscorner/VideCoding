import json
from pathlib import Path
from typing import Any


class ProfileManager:
    """Named sync profiles: profile name -> {source, dest, recursive, file_mask, hash_verify}."""

    def __init__(self, profiles_path: Path):
        self.profiles_path = profiles_path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self) -> bool:
        try:
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
            return True
        except OSError:
            return False

    def names(self) -> list[str]:
        return sorted(self._data.keys())

    def get(self, name: str) -> dict[str, Any] | None:
        return self._data.get(name)

    def save_profile(self, name: str, values: dict[str, Any]) -> bool:
        self._data[name] = values
        return self._save()

    def delete_profile(self, name: str) -> bool:
        if name in self._data:
            del self._data[name]
            return self._save()
        return False
