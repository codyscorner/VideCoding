import os
import threading
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
    merging = pyqtSignal(str)  # filename: all bytes sent, waiting on server-side multipart merge
    merging_status = pyqtSignal(str, int, int)  # filename, merge tmp bytes (-1 if not visible), elapsed seconds
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
                merge_notified = False
                merge_poll_stop = threading.Event()

                def cb(chunk_bytes, _job=job, _stop=merge_poll_stop):
                    nonlocal job_bytes_done, merge_notified
                    job_bytes_done += chunk_bytes
                    self.progress.emit(
                        completed_bytes + job_bytes_done,
                        self._total_bytes,
                        _job.display_name,
                        i,
                        len(self.jobs),
                    )
                    # Every byte is on the wire; anything after this is RunPod
                    # merging the multipart chunks server-side, which emits no
                    # further transfer callbacks — poll the parent prefix for
                    # the .s3compat-merge-*.tmp file so the UI can show the
                    # merge is still alive.
                    if _job.direction == "upload" and not merge_notified and job_bytes_done >= _job.size:
                        merge_notified = True
                        self.merging.emit(_job.display_name)
                        threading.Thread(
                            target=self._poll_merge, args=(_job, _stop), daemon=True
                        ).start()

                try:
                    if job.direction == "upload":
                        self.client.upload_file(job.local_path, job.key, progress_callback=cb)
                    else:
                        os.makedirs(os.path.dirname(job.local_path), exist_ok=True)
                        self.client.download_file(job.key, job.local_path, progress_callback=cb)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    # An upload can fail on the final CompleteMultipartUpload
                    # response (e.g. timeout during RunPod's server-side merge)
                    # even though the object actually landed — check before
                    # re-uploading the whole file.
                    if job.direction == "upload" and self._upload_already_landed(job):
                        last_error = None
                        break
                    # RunPod's endpoint occasionally rejects the SDK's internal
                    # HeadObject/GetObject with a transient 403/5xx under a
                    # burst of requests (e.g. a whole-folder download) even
                    # though the object is fine — retry before giving up.
                    # A flat 1s delay wasn't always enough for RunPod to
                    # recover, so back off exponentially (1s, 2s, 4s, 8s, 16s).
                    last_error = exc
                    if attempt < TRANSFER_RETRY_ATTEMPTS:
                        time.sleep(TRANSFER_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
                finally:
                    merge_poll_stop.set()

            if last_error is not None:
                errors.append((job.key, str(last_error)))
            completed_bytes += job.size
            self.progress.emit(completed_bytes, self._total_bytes, job.display_name, i + 1, len(self.jobs))
        self.finished.emit(errors)

    def _poll_merge(self, job: TransferJob, stop_event: threading.Event):
        """While the blocking CompleteMultipartUpload call waits on RunPod's
        server-side merge, watch the parent prefix for the merge tmp file so
        the UI can report that the merge is still in progress."""
        parent = job.key.rsplit("/", 1)[0] + "/" if "/" in job.key else ""
        started = time.time()
        while not stop_event.wait(5.0):
            try:
                tmp_size = self.client.get_merge_tmp_size(parent)
            except Exception:  # noqa: BLE001
                continue
            if stop_event.is_set():
                break
            self.merging_status.emit(
                job.display_name,
                tmp_size if tmp_size is not None else -1,
                int(time.time() - started),
            )

    def _upload_already_landed(self, job: TransferJob) -> bool:
        try:
            return self.client.get_object_size(job.key) == job.size
        except Exception:  # noqa: BLE001
            return False
