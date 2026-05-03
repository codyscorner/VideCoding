import json
import os
import sys


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DEFAULT_PREFIX = "All_PC_Images_backup"

DEFAULTS = {
    "last_source_folder": "",
    "last_destination_path": "",
    "last_archive_date": "",
    "7zip_path": "",
    "archive_prefix": DEFAULT_PREFIX,
    "compression_level": "store",
}


def load_settings():
    path = os.path.join(get_app_dir(), "settings.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for k, v in DEFAULTS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return DEFAULTS.copy()


def save_settings(settings):
    path = os.path.join(get_app_dir(), "settings.json")
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
