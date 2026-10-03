"""Settings for AI Image Studio — settings.json next to the EXE.

The tabs keep reading and writing the plain dict (`config.data`) they always
used; the RunPod modules copied from the ComfyUI Video Creator talk to the
same dict through get/set/save. One dict, so neither side can overwrite the
other's changes with a stale copy.
"""

import json
import sys
from pathlib import Path
from typing import Any


def app_dir() -> Path:
    """Folder next to the EXE (or ai_image_generator.py from source) — every
    portable file this app owns (settings, api_keys.json, history, workflows,
    runpod_session.json, pod log) lives here. Path(__file__) would point into
    PyInstaller's temp extraction folder, which is wiped on every exit."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


# Pre-3.3.0 every generating tab had its own Connection box.
_OLD_TAB_PREFIXES = ("t2i", "edit", "i2i")


class ConfigManager:
    DEFAULT = {
        # One connection for the whole app (v3.3.0). PodControl rewrites mode
        # and runpod_url when it starts or adopts a pod.
        "mode": "local",
        "comfyui_url": "http://127.0.0.1:8188",
        "runpod_url": "",
        # RunPod pod control (copied from ComfyUI Video Creator). The API key is
        # NOT here — it lives in api_keys.json next to the EXE (see runpod_api.py).
        "runpod_gpu_order": [],                # GPU models, best first; outranks runpod_pod_order
        "runpod_pod_order": [],                # pod IDs, best first within a GPU model
        "runpod_auto_prompt": True,            # offer to start a pod on launch
        "runpod_auto_stop_on_exit": True,      # ask to stop the connected pod when quitting
        "runpod_spend_limit": 0.0,             # USD per pod run; 0 = no limit
        "runpod_idle_stop_min": 0,             # stop the pod this long after the last run; 0 = off
        "runpod_spend_warn_fraction": 0.8,
        # "Keep trying" when every pod is busy
        "runpod_retry_interval_min": 10,       # minutes between sweeps of the pod list
        "runpod_retry_window_min": 120,        # give up after this long
        # One sound for everything worth walking back for: pod found, gave up,
        # run / queue finished
        "alert_sound_path": "",
        "alert_sound_enabled": True,
        # Model check & sync with the pod volume (copied from Video Creator,
        # see model_sync.py). Blank S3 fields = the check stays off.
        "model_check_enabled": True,
        "model_sync_download": False,          # also pull pod-only files down to this PC
        "models_dir": "",                      # local ComfyUI/models root
        "s3_profile_name": "runpod-s3",
        "s3_region": "",
        "s3_endpoint_url": "",
        "s3_bucket_name": "",
        "s3_models_prefix": "runpod-slim/ComfyUI/models/",
    }

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data = self._load()
        if self._migrate():
            self.save()

    def _load(self) -> dict:
        data = {}
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        # Defaults only fill gaps; the tabs' own keys pass straight through.
        merged = dict(self.DEFAULT)
        merged.update(data if isinstance(data, dict) else {})
        return merged

    def _migrate(self) -> bool:
        """Fold the old per-tab connections into the one app connection.
        Text to Image's choice wins (it was the tab people actually used),
        then Scene Composer's, then Variations'."""
        old = [p for p in _OLD_TAB_PREFIXES if f"{p}_conn_mode" in self._data]
        if not old:
            return False
        first = old[0]
        self._data["mode"] = self._data.get(f"{first}_conn_mode", "local") or "local"
        for p in old:
            url = (self._data.get(f"{p}_url") or "").strip()
            if url and self._data["comfyui_url"] == self.DEFAULT["comfyui_url"]:
                self._data["comfyui_url"] = url
            pod = (self._data.get(f"{p}_runpod_url") or "").strip()
            if pod and not self._data.get("runpod_url"):
                self._data["runpod_url"] = pod
        for p in _OLD_TAB_PREFIXES:
            for suffix in ("_conn_mode", "_url", "_runpod_url", "_runpod_endpoint"):
                self._data.pop(p + suffix, None)
        return True

    @property
    def data(self) -> dict:
        """The live dict the tabs read and write directly."""
        return self._data

    def save(self) -> bool:
        try:
            self.config_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_all(self) -> dict:
        return self._data.copy()

    # Convenience (PodControl asks these) ------------------------------
    def server_url(self) -> str:
        if self.is_runpod():
            return (self.get("runpod_url", "") or "").strip().rstrip("/")
        return (self.get("comfyui_url", "") or "").strip().rstrip("/")

    def is_runpod(self) -> bool:
        return self.get("mode", "local") == "runpod"
