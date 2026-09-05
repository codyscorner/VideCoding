import json
import os
from typing import Optional

class AppSettings:
    def __init__(self):
        self.last_opened_folder: Optional[str] = None
        # String representation of window geometry (e.g. base64 encoded QByteArray)
        self.geometry: Optional[str] = None

    @classmethod
    def load(cls, path: str) -> "AppSettings":
        settings = cls()
        if not os.path.exists(path):
            return settings
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings.last_opened_folder = data.get("last_opened_folder")
                settings.geometry = data.get("geometry")
        except (OSError, json.JSONDecodeError):
            # Gracefully handle missing or invalid file by returning defaults
            pass
            
        return settings

    def save(self, path: str) -> None:
        data = {
            "last_opened_folder": self.last_opened_folder,
            "geometry": self.geometry
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except OSError:
            # Handle cases where writing to the file fails (like permissions)
            pass
