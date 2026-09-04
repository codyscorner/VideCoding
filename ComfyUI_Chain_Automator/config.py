import json
from pathlib import Path
from typing import Any


class ConfigManager:
    DEFAULT = {
        "comfyui_url": "http://127.0.0.1:8188",
        "input_dir": "P:/AI/ComfyLocal/ComfyUI_windows_portable/ComfyUI/input",
        "output_base_dir": "P:/AI/ComfyLocal/ComfyUI_windows_portable/ComfyUI/output/video/Merge",
        "workflow_dir": "P:/AI/ComfyLocal/ComfyUI_windows_portable/Workflow_API",
        "workflows": [],
        "anthropic_api_key": "",
        "lora_check_enabled": True,
        "s3_profile_name": "runpod-s3",
        "s3_region": "",
        "s3_endpoint_url": "",
        "s3_bucket_name": "",
        "s3_loras_prefix": "runpod-slim/ComfyUI/models/loras/"
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
