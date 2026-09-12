"""Qt wrappers around runpod_api.

Waking a pod takes anywhere from fifteen seconds to five minutes, so none of it
can happen on the UI thread — the existing Test Connection button in
settings_dialog already blocks the window for its 15s timeout, and that is the
pattern to avoid here, not copy.

All the logic lives in runpod_api; these classes only move it off the GUI thread
and turn its log callback into signals.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

import runpod_api


class PodStartWorker(QThread):
    """Walks the priority list and brings up the first pod that works."""

    log = pyqtSignal(str)              # one progress line
    ready = pyqtSignal(str, str)       # pod_id, comfy url
    exhausted = pyqtSignal(str)        # no pod available; summary for the dialog
    failed = pyqtSignal(str)           # key/account problem — chain abandoned

    def __init__(self, pod_ids: list[str], gpu_order: list[str] | None = None):
        super().__init__()
        self._pod_ids = list(pod_ids)
        self._gpu_order = list(gpu_order or [])
        self._cancelled = False
        self._misses: list[str] = []

    def cancel(self):
        """Cooperative — the chain checks between polls, so a cancel lands
        within a few seconds and stops any pod it had half-started."""
        self._cancelled = True

    def run(self):
        try:
            got = runpod_api.wake_first_available(
                self._pod_ids,
                log=self.log.emit,
                should_cancel=lambda: self._cancelled,
                misses_out=self._misses,
                gpu_order=self._gpu_order,
            )
        except runpod_api.Fatal as e:
            self.failed.emit(str(e))
            return
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}")
            return

        if self._cancelled:
            return
        if got is None:
            self.exhausted.emit("\n".join(self._misses))
            return
        self.ready.emit(got[0], got[1])


class PodStopWorker(QThread):
    """Stops one pod. Used by the Stop button and by the auto-stop on exit."""

    done = pyqtSignal(str, bool)       # pod_id, succeeded

    def __init__(self, pod_id: str):
        super().__init__()
        self._pod_id = pod_id

    def run(self):
        self.done.emit(self._pod_id, runpod_api.stop_pod(self._pod_id))


class PodListWorker(QThread):
    """Fetches the account's pods for the ordering list in Settings."""

    done = pyqtSignal(list, str)       # pods, error

    def run(self):
        try:
            self.done.emit(runpod_api.list_pods(), "")
        except runpod_api.RunPodError as e:
            self.done.emit([], str(e))
        except Exception as e:  # noqa: BLE001
            self.done.emit([], f"{type(e).__name__}: {e}")
