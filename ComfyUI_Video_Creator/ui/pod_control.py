"""Header widget that starts, watches and stops the RunPod pod.

Owns everything pod-related so main_window only has to place it and answer one
question — "is a generation running right now?" — which decides whether hitting
the spend limit stops the pod immediately or waits for the current job.

See RUNPOD_POD_CONTROL_PLAN.md for the design and the reasoning behind the
zero-GPU check and the soft spend limit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QPushButton, QWidget,
)

import runpod_api
from config import app_dir
from ui.pod_worker import PodStartWorker, PodStopWorker
from ui.styles import COLORS

# Remembers the pod this app started, so a crash can be cleaned up next launch
# and so auto-stop never touches a pod someone started in the console.
SESSION_FILE = "runpod_session.json"

POLL_MS = 60_000        # spend moves by cents; once a minute is plenty


class PodControl(QWidget):
    server_changed = pyqtSignal()      # pod came up / went away — refresh the mode label
    log = pyqtSignal(str)              # progress lines, echoed into the active run panel

    def __init__(self, config, is_busy: Callable[[], bool], parent=None):
        super().__init__(parent)
        self._config = config
        self._is_busy = is_busy
        self._pod_id = ""              # the pod THIS app started
        self._start_worker: PodStartWorker | None = None
        self._stop_worker: PodStopWorker | None = None
        self._progress: QProgressDialog | None = None
        self._stop_when_idle = False
        self._warned = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._spend_lbl = QLabel("")
        self._spend_lbl.setObjectName("subtitle")
        lay.addWidget(self._spend_lbl)
        self._btn = QPushButton("Start Pod")
        self._btn.setObjectName("secondary_btn")
        self._btn.clicked.connect(self._on_button)
        lay.addWidget(self._btn)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)
        self._refresh_button()

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    @property
    def pod_id(self) -> str:
        return self._pod_id

    def _session_path(self) -> Path:
        return Path(self._config.get("_base_dir", str(app_dir()))) / SESSION_FILE

    def _remember(self, pod_id: str):
        self._pod_id = pod_id
        try:
            with open(self._session_path(), "w", encoding="utf-8") as f:
                json.dump({"pod_id": pod_id}, f)
        except OSError:
            pass

    def _forget(self):
        self._pod_id = ""
        try:
            self._session_path().unlink(missing_ok=True)
        except OSError:
            pass

    def _refresh_button(self):
        running = bool(self._pod_id)
        self._btn.setText("Stop Pod" if running else "Start Pod")
        self._btn.setEnabled(self._start_worker is None and self._stop_worker is None)
        if not running:
            self._spend_lbl.setText("")

    # ------------------------------------------------------------------ #
    # Launch
    # ------------------------------------------------------------------ #

    def check_on_launch(self):
        """Crash recovery first, then the optional 'start a pod?' prompt."""
        if not runpod_api.have_key():
            return
        if self._recover_orphan():
            return
        if not self._config.get("runpod_auto_prompt", True):
            return
        ans = QMessageBox.question(
            self, "RunPod",
            "Start a RunPod pod for this session?\n\n"
            "Your pods will be tried in order and the first available one used.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.start_chain()

    def _recover_orphan(self) -> bool:
        """A pod left running because the app died without its closeEvent."""
        try:
            with open(self._session_path(), "r", encoding="utf-8") as f:
                pod_id = (json.load(f).get("pod_id") or "").strip()
        except (OSError, ValueError):
            return False
        if not pod_id:
            self._forget()
            return False
        try:
            pod = runpod_api.get_pod(pod_id)
        except runpod_api.RunPodError:
            self._forget()
            return False
        if not runpod_api.is_healthy(pod):
            self._forget()
            return False

        spent = runpod_api.spend_so_far(pod)
        ans = QMessageBox.question(
            self, "Pod still running",
            f"Video Creator didn't shut down cleanly last time and "
            f"{pod.get('name') or pod_id} is still running.\n\n"
            f"Up {runpod_api.format_duration(runpod_api.uptime_seconds(pod))}, "
            f"about ${spent:.2f} of compute so far.\n\nKeep using it, or stop it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        self._adopt(pod_id, runpod_api.proxy_url(pod_id))
        if ans == QMessageBox.StandardButton.No:
            self.stop_pod()
        return True

    # ------------------------------------------------------------------ #
    # Start / stop
    # ------------------------------------------------------------------ #

    def _on_button(self):
        self.stop_pod() if self._pod_id else self.start_chain()

    def start_chain(self):
        if self._start_worker is not None:
            return
        if not runpod_api.have_key():
            QMessageBox.warning(self, "No API key",
                                f"Add your RunPod key to {runpod_api.KEY_FILE_NAME} next to the app.")
            return

        order = list(self._config.get("runpod_pod_order", []) or [])
        self._progress = QProgressDialog("Looking for an available pod…", "Cancel", 0, 0, self)
        self._progress.setWindowTitle("Starting RunPod")
        self._progress.setMinimumWidth(460)
        self._progress.setMinimumDuration(0)
        self._progress.canceled.connect(self._cancel_start)

        self._start_worker = PodStartWorker(order)
        self._start_worker.log.connect(self._on_progress)
        self._start_worker.ready.connect(self._on_ready)
        self._start_worker.exhausted.connect(self._on_exhausted)
        self._start_worker.failed.connect(self._on_failed)
        self._start_worker.finished.connect(self._start_finished)
        self._start_worker.start()
        self._refresh_button()

    def _cancel_start(self):
        if self._start_worker is not None:
            self._start_worker.cancel()

    def _on_progress(self, msg: str):
        if self._progress is not None:
            self._progress.setLabelText(msg)
        self.log.emit(msg)

    def _close_progress(self):
        if self._progress is not None:
            self._progress.close()
            self._progress = None

    def _start_finished(self):
        self._start_worker = None
        self._close_progress()
        self._refresh_button()

    def _adopt(self, pod_id: str, url: str):
        """Point the app at this pod and switch to RunPod mode."""
        self._remember(pod_id)
        self._warned = False
        self._stop_when_idle = False
        self._config.set("runpod_url", url)
        self._config.set("mode", "runpod")
        self._config.save()
        self.server_changed.emit()
        self._refresh_button()
        self._poll()

    def _on_ready(self, pod_id: str, url: str):
        self._adopt(pod_id, url)
        self.log.emit(f"RunPod: {pod_id} ready at {url}")

    def _on_exhausted(self, summary: str):
        self._close_progress()
        box = QMessageBox(self)
        box.setWindowTitle("No pods available")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("None of your current pods are available to start.\n\n"
                    "This usually means the machines they're pinned to have their "
                    "GPUs rented out right now.\n\nSwitch to Local?")
        if summary:
            # Per-pod reasons, so "nothing available" can be told apart from
            # "every attempt failed for the same unexpected reason".
            box.setDetailedText(summary)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        ans = box.exec()
        if ans == QMessageBox.StandardButton.Yes:
            self._config.set("mode", "local")
            self._config.save()
            self.server_changed.emit()

    def _on_failed(self, msg: str):
        self._close_progress()
        QMessageBox.warning(self, "RunPod", msg)

    def stop_pod(self, quiet: bool = False):
        if not self._pod_id or self._stop_worker is not None:
            return
        pod_id = self._pod_id
        self._stop_worker = PodStopWorker(pod_id)
        self._stop_worker.done.connect(lambda pid, ok: self._on_stopped(pid, ok, quiet))
        self._stop_worker.finished.connect(self._stop_finished)
        self._stop_worker.start()
        self._btn.setEnabled(False)

    def _on_stopped(self, pod_id: str, ok: bool, quiet: bool):
        self.log.emit(f"RunPod: {pod_id} " + ("stopped" if ok else "could NOT be stopped"))
        if ok:
            self._forget()
            self.server_changed.emit()
        elif not quiet:
            QMessageBox.warning(self, "RunPod",
                                f"Couldn't stop {pod_id}. Stop it in the RunPod console so it "
                                "doesn't keep billing.")

    def _stop_finished(self):
        self._stop_worker = None
        self._refresh_button()

    # ------------------------------------------------------------------ #
    # Spend
    # ------------------------------------------------------------------ #

    def _poll(self):
        if not self._pod_id or self._start_worker is not None:
            return
        try:
            pod = runpod_api.get_pod(self._pod_id)
        except runpod_api.RunPodError:
            return                      # transient; try again next tick
        if not runpod_api.is_healthy(pod):
            # Stopped from the console, or lost its GPU underneath us.
            self.log.emit(f"RunPod: {self._pod_id} is no longer running")
            self._forget()
            self.server_changed.emit()
            self._refresh_button()
            return

        limit = float(self._config.get("runpod_spend_limit", 0) or 0)
        warn_at = float(self._config.get("runpod_spend_warn_fraction", 0.8) or 0.8)
        state = runpod_api.limit_state(pod, limit, warn_at)
        summary = runpod_api.spend_summary(pod)

        color = {"warn": COLORS["warning"], "over": COLORS["error"]}.get(state, COLORS["fg_dim"])
        if limit > 0:
            summary += f" / ${limit:.2f}"
        self._spend_lbl.setText(f"<span style='color:{color}'>{summary}</span>")

        if state == "warn" and not self._warned:
            self._warned = True
            left = runpod_api.projected_runtime(pod, limit)
            self.log.emit(f"RunPod: ${runpod_api.spend_so_far(pod):.2f} of ${limit:.2f} spent — "
                          f"about {runpod_api.format_duration(left)} of GPU time left")
        elif state == "over":
            self._hit_limit(pod)

    def _hit_limit(self, pod: dict):
        if self._stop_when_idle:
            if not self._is_busy():
                self._stop_when_idle = False
                self.log.emit("RunPod: spend limit reached — stopping the pod")
                self.stop_pod(quiet=True)
            return
        self._stop_when_idle = True
        if self._is_busy():
            self.log.emit(f"RunPod: spend limit of ${float(self._config.get('runpod_spend_limit', 0)):.2f} "
                          "reached — finishing this run, then stopping the pod")
        else:
            self._stop_when_idle = False
            self.log.emit("RunPod: spend limit reached — stopping the pod")
            self.stop_pod(quiet=True)

    def over_limit(self) -> bool:
        """main_window asks before starting a new run."""
        return self._stop_when_idle

    def run_finished(self):
        """Called when a generation ends, so a deferred stop can happen now."""
        if self._stop_when_idle and not self._is_busy():
            self._stop_when_idle = False
            self.log.emit("RunPod: spend limit reached — stopping the pod")
            self.stop_pod(quiet=True)

    # ------------------------------------------------------------------ #
    # Exit
    # ------------------------------------------------------------------ #

    def shutdown(self):
        """Stop the pod synchronously — the app is closing, so a QThread would
        be torn down before it ever sent the request."""
        self._timer.stop()
        if self._start_worker is not None:
            self._start_worker.cancel()
            self._start_worker.wait(3000)
        if not self._pod_id:
            return
        if not self._config.get("runpod_auto_stop_on_exit", True):
            return
        runpod_api.stop_pod(self._pod_id)
        self._forget()
