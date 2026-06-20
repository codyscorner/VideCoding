"""One-shot worker that checks for CLIP model updates at startup."""

import threading
import urllib.request
import json
import pathlib
import os
from PySide6.QtCore import QThread, Signal

UPDATE_CHECK_TIMEOUT = 4  # seconds


class ModelUpdateWorker(QThread):
    """
    Runs once at startup. Checks HuggingFace for a newer model revision.
    If found, emits update_available so the UI can prompt the user.
    If the user confirms, call start_download() to fetch with progress.
    """

    update_available = Signal(str)          # remote SHA
    download_progress = Signal(int, int, str)  # bytes_done, bytes_total, filename
    download_complete = Signal()
    download_failed = Signal(str)

    def __init__(self, model_name: str = "clip-ViT-B-32", parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self._download_confirmed = False
        self._response_event = threading.Event()

    # ------------------------------------------------------------------ public

    def confirm_download(self, yes: bool) -> None:
        """Called from the main thread after the user responds to the prompt."""
        self._download_confirmed = yes
        self._response_event.set()

    # ----------------------------------------------------------------- private

    def run(self) -> None:
        remote_sha = self._check_for_update()
        if not remote_sha:
            return

        # Ask the user
        self._response_event.clear()
        self.update_available.emit(remote_sha)
        self._response_event.wait()

        if self._download_confirmed:
            self._download_model()

    def _check_for_update(self) -> str:
        """Return remote SHA if newer than cached, else empty string."""
        try:
            repo_id = f"sentence-transformers/{self.model_name}"
            url = f"https://huggingface.co/api/models/{repo_id}"
            req = urllib.request.Request(url, headers={"User-Agent": "ImageDedupeSearch"})
            with urllib.request.urlopen(req, timeout=UPDATE_CHECK_TIMEOUT) as resp:
                data = json.loads(resp.read())
            remote_sha = data.get("sha", "")

            cache_base = pathlib.Path(os.path.expanduser("~/.cache/huggingface/hub"))
            slug = f"models--sentence-transformers--{self.model_name}"
            snapshots = cache_base / slug / "snapshots"
            if snapshots.exists():
                local_revs = list(snapshots.iterdir())
                if local_revs and remote_sha and local_revs[0].name != remote_sha:
                    return remote_sha
            return ""
        except Exception:
            return ""

    def _download_model(self) -> None:
        try:
            import huggingface_hub as hfh

            repo_id = f"sentence-transformers/{self.model_name}"

            files = list(hfh.list_repo_tree(repo_id, recursive=True))
            file_entries = [f for f in files if hasattr(f, "size") and f.size]
            total_bytes = sum(f.size for f in file_entries)
            done_bytes = 0

            for entry in file_entries:
                fname = entry.path
                self.download_progress.emit(done_bytes, total_bytes, fname)
                hfh.hf_hub_download(repo_id=repo_id, filename=fname)
                done_bytes += entry.size
                self.download_progress.emit(done_bytes, total_bytes, fname)

            self.download_complete.emit()
        except Exception as e:
            self.download_failed.emit(str(e))
