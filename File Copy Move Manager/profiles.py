"""Profile management for File Copy Move Manager"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ProfileManager:
    """Manages saved configuration profiles"""

    PROFILE_KEYS = [
        "source_folder",
        "dest_folder",
        "extension",
        "preserve_structure",
        "number_duplicates",
        "recursive_search",
        "folder_structure",
        "verify_checksum",
        "incremental",
        "workers",
        "enable_size_filter",
        "min_size",
        "max_size",
        "size_unit",
        "enable_date_filter",
        "days_old",
    ]

    def __init__(self, profiles_path: Path):
        self.profiles_path = profiles_path
        self._profiles: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self) -> bool:
        try:
            with open(self.profiles_path, 'w') as f:
                json.dump(self._profiles, f, indent=4)
            return True
        except OSError:
            return False

    def get_profile_names(self) -> List[str]:
        return sorted(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        return self._profiles.get(name)

    def save_profile(self, name: str, settings: Dict[str, Any]) -> bool:
        profile_data = {key: settings[key] for key in self.PROFILE_KEYS if key in settings}
        profile_data["_created"] = self._profiles.get(name, {}).get(
            "_created", datetime.now().isoformat()
        )
        profile_data["_modified"] = datetime.now().isoformat()
        self._profiles[name] = profile_data
        return self._save()

    def delete_profile(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            return self._save()
        return False

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        if old_name in self._profiles and new_name not in self._profiles:
            self._profiles[new_name] = self._profiles.pop(old_name)
            self._profiles[new_name]["_modified"] = datetime.now().isoformat()
            return self._save()
        return False

    def profile_exists(self, name: str) -> bool:
        return name in self._profiles

    def duplicate_profile(self, source_name: str, new_name: str) -> bool:
        if source_name in self._profiles and new_name not in self._profiles:
            copy = self._profiles[source_name].copy()
            copy["_created"] = datetime.now().isoformat()
            copy["_modified"] = datetime.now().isoformat()
            self._profiles[new_name] = copy
            return self._save()
        return False
