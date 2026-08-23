import os
import time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

TRANSFER_RETRY_ATTEMPTS = 6
TRANSFER_RETRY_BASE_DELAY_SECONDS = 1.0


class ActionWorker(QThread):
    """Runs a single callable on a background thread and reports result/error."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
            return
        self.finished.emit(result)


@dataclass
class TransferJob:
    local_path: str
    key: str
    size: int
    direction: str  # "upload" or "download"
    display_name: str


class TransferWorker(QThread):
    progress = pyqtSignal(int, int, str, int, int)  # bytes_done, bytes_total, filename, files_done, files_total
    finished = pyqtSignal(list)  # list of (key, error_str)

    def __init__(self, client, jobs: list[TransferJob]):
        super().__init__()
        self.client = client
        self.jobs = jobs
        self._cancelled = False
        self._total_bytes = sum(job.size for job in jobs)

    def cancel(self):
        self._cancelled = True

    def run(self):
        errors: list[tuple[str, str]] = []
        completed_bytes = 0
        for i, job in enumerate(self.jobs):
            if self._cancelled:
                break

            last_error: Exception | None = None
            for attempt in range(1, TRANSFER_RETRY_ATTEMPTS + 1):
                if self._cancelled:
                    break
                job_bytes_done = 0

                def cb(chunk_bytes, _job=job):
                    nonlocal job_bytes_done
                    job_bytes_done += chunk_bytes
                    self.progress.emit(
                        completed_bytes + job_bytes_done,
                        self._total_bytes,
                        _job.display_name,
                        i,
                        len(self.jobs),
                    )

                try:
                    if job.direction == "upload":
                        self.client.upload_file(job.local_path, job.key, progress_callback=cb)
                    else:
                        os.makedirs(os.path.dirname(job.local_path), exist_ok=True)
                        self.client.download_file(job.key, job.local_path, progress_callback=cb)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    # RunPod's endpoint occasionally rejects the SDK's internal
                    # HeadObject/GetObject with a transient 403/5xx under a
                    # burst of requests (e.g. a whole-folder download) even
                    # though the object is fine — retry before giving up.
                    # A flat 1s delay wasn't always enough for RunPod to
                    # recover, so back off exponentially (1s, 2s, 4s, 8s, 16s).
                    last_error = exc
                    if attempt < TRANSFER_RETRY_ATTEMPTS:
                        time.sleep(TRANSFER_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))

            if last_error is not None:
                errors.append((job.key, str(last_error)))
            completed_bytes += job.size
            self.progress.emit(completed_bytes, self._total_bytes, job.display_name, i + 1, len(self.jobs))
        self.finished.emit(errors)
