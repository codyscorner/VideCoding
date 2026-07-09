import json
from pathlib import Path


class RatingsStore:
    """Per-image ratings (0-5 stars) and flags, persisted to a JSON file
    next to the app, keyed by absolute file path."""

    def __init__(self, store_file: Path):
        self.store_file = store_file
        self._data: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if self.store_file.exists():
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self._data = {
                        k: v for k, v in raw.items() if isinstance(v, dict)
                    }
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def save(self) -> None:
        try:
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            print(f"Ratings save error: {e}")

    @staticmethod
    def _key(path: str) -> str:
        return str(Path(path).resolve())

    def get_rating(self, path: str) -> int:
        return int(self._data.get(self._key(path), {}).get("rating", 0))

    def is_flagged(self, path: str) -> bool:
        return bool(self._data.get(self._key(path), {}).get("flagged", False))

    def set_rating(self, path: str, rating: int) -> None:
        rating = max(0, min(5, int(rating)))
        entry = self._data.setdefault(self._key(path), {})
        entry["rating"] = rating
        self._prune(path)
        self.save()

    def toggle_flag(self, path: str) -> bool:
        entry = self._data.setdefault(self._key(path), {})
        entry["flagged"] = not entry.get("flagged", False)
        new_state = entry["flagged"]
        self._prune(path)
        self.save()
        return new_state

    def remove(self, path: str) -> None:
        if self._data.pop(self._key(path), None) is not None:
            self.save()

    def _prune(self, path: str) -> None:
        # Drop entries that carry no information (0 stars, not flagged)
        key = self._key(path)
        entry = self._data.get(key)
        if entry and not entry.get("rating") and not entry.get("flagged"):
            del self._data[key]
