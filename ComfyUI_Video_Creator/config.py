"""Portable config for ComfyUI Video Creator.

The settings file lives next to the EXE (or next to main.py when run from
source) — never in %APPDATA% — because every VibeCoded app is a portable
single-file EXE that must work from a thumb drive.
"""

import json
import sys
from pathlib import Path
from typing import Any

CONFIG_NAME = "video_creator_config.json"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


class ConfigManager:
    DEFAULT: dict[str, Any] = {
        # ComfyUI server
        "mode": "local",                       # local | runpod
        "comfyui_url": "http://127.0.0.1:8000",
        "runpod_url": "",
        # Folders
        "image_dir": "",
        "video_dir": "",
        "workflow_dir": "P:/AI/ComfyLocal/ComfyUI_windows_portable/Workflow_API",
        "output_dir": "",
        "loras_dir": "P:/AI/ComfyLocal/ComfyUI_windows_portable/ComfyUI/models/loras",
        # Staging for workflows that read a whole folder (LoadImageListFromDir)
        "staging_dir_local": "",
        "runpod_input_dir": "/workspace/runpod-slim/ComfyUI/input",
        # Tools
        "ffmpeg_path": "",
        # Remembered UI state
        "image_workflow": "",
        "video_workflow": "",
        "image_sort": "Name A→Z",
        "video_sort": "Newest First",
        "video_input_mode": "auto",            # auto | last_frame | upload_video
        "extend_stitch": True,
        "seed_mode": "random",                 # random | fixed
        "seed_value": 0,
        "prompt_font_size": 10,
        "panel_split_image": [],
        "panel_split_video": [],
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
        return dict(self.DEFAULT)

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
        return dict(self._data)

    # Convenience -------------------------------------------------------
    def server_url(self) -> str:
        if self.get("mode", "local") == "runpod":
            return (self.get("runpod_url", "") or "").strip().rstrip("/")
        return (self.get("comfyui_url", "") or "").strip().rstrip("/")

    def is_runpod(self) -> bool:
        return self.get("mode", "local") == "runpod"
