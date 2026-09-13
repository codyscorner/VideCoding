"""Header widget that starts, watches and stops the RunPod pod.

Owns everything pod-related so main_window only has to place it and answer one
question — "is a generation running right now?" — which decides whether hitting
the spend limit stops the pod immediately or waits for the current job.

See RUNPOD_POD_CONTROL_PLAN.md for the design and the reasoning behind the
zero-GPU check and the soft spend limit.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressDialog, QPushButton,
    QStyleFactory, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import alerts
import runpod_api
from config import app_dir
from ui.pod_worker import PodStartWorker, PodStopWorker
from ui.styles import COLORS

# Remembers the pod this app started, so a crash can be cleaned up next launch
# and so auto-stop never touches a pod someone started in the console.
SESSION_FILE = "runpod_session.json"

# The chain's progress used to exist only in the on-screen log, which made an
# intermittent "it said no but the pod was fine" impossible to investigate after
# the fact. Every line is now also appended here, with a timestamp.
POD_LOG = "runpod_pod.log"
POD_LOG_MAX_LINES = 2000

POLL_MS = 60_000        # spend moves by cents; once a minute is plenty


class RunningPodDialog(QDialog):
    """Launch-time chooser: the pods that are up right now, with live status,
    and what to do about them. `choice` is "use" / "start" / "stop" / "skip"
    after exec(); `selected_id` is the highlighted pod."""

    def __init__(self, running: list[dict], opener: str, session_id: str = "",
                 configured_id: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("RunPod — pods already running")
        self.choice = "skip"
        self._ids = [p.get("id", "") for p in running]
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(opener + "\n\nUse one for this session, start another, or stop one."))
        # Column widths are budgets in characters, not measurements of the
        # current text: a pod name or GPU longer than its budget elides, a
        # short one leaves room. Measured in the real font, plus the cell
        # padding and the style's own margins, so nothing clips at any font.
        COLS = (("#", 3), ("Pod", 25), ("GPU", 25), ("Up", 10), ("$/hr", 10), ("Spent", 10), ("", 20))
        self._table = QTableWidget(len(running), len(COLS), self)
        self._table.setHorizontalHeaderLabels([c for c, _ in COLS])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)      # no dotted focus cell
        # The native Windows style paints its own per-cell highlight frame on
        # the selected row (a light edge at every cell boundary) regardless of
        # the stylesheet; Fusion paints exactly what the stylesheet says.
        self._table.setStyle(QStyleFactory.create("Fusion"))
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.horizontalHeader().setSectionsClickable(False)
        for row, pod in enumerate(running):
            pid = pod.get("id", "")
            note = ("this app's pod" if pid == session_id
                    else "current connection" if pid == configured_id else "")
            gpu = ((pod.get("gpu") or {}).get("id") or "?").replace("NVIDIA ", "").replace(" Server Edition", "")
            cells = [str(row + 1), pod.get("name") or pid, gpu,
                     runpod_api.format_duration(runpod_api.uptime_seconds(pod)),
                     f"${runpod_api.hourly_cost(pod):.2f}", f"${runpod_api.spend_so_far(pod):.2f}", note]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)    # matches the headers
                self._table.setItem(row, col, item)
        PAD = 10                                   # matches the ::item padding below
        header = self._table.horizontalHeader()
        fm = self._table.fontMetrics()
        total = 0
        for col, (_label, chars) in enumerate(COLS):
            width = fm.horizontalAdvance("0" * chars) + 2 * PAD + 16
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(col, width)
            total += width
        header.setStretchLastSection(True)         # the note column absorbs any remainder
        self._table.setStyleSheet(
            f"QTableWidget {{ background-color: {COLORS['bg_input']}; color: {COLORS['fg_primary']};"
            f" border: 1px solid {COLORS['border']}; outline: none; }}"
            f"QTableWidget::item {{ padding: 6px {PAD}px; border: none; }}"
            f"QTableWidget::item:selected {{ background-color: {COLORS['accent']}; color: {COLORS['fg_primary']}; }}"
            f"QTableWidget::item:focus {{ border: none; outline: none; }}"
            f"QHeaderView::section {{ background-color: {COLORS['bg_light']}; color: {COLORS['fg_secondary']};"
            f" border: none; border-bottom: 1px solid {COLORS['border']}; padding: 6px {PAD}px; font-weight: bold; }}")
        # One line per pod, tall enough for the rows it has (up to six).
        row_h = fm.height() + 14
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._table.verticalHeader().setDefaultSectionSize(row_h)
        rows_h = row_h * min(len(running), 6)
        self._table.setFixedHeight(header.height() + rows_h + 2 * self._table.frameWidth() + 4)
        self.setMinimumWidth(total + 2 * self._table.frameWidth() + 40)
        self._table.selectRow(0)
        self._table.doubleClicked.connect(lambda *_: self._pick("use"))
        lay.addWidget(self._table)
        row = QHBoxLayout()
        for label, choice in (("Use selected", "use"), ("Start another pod", "start"),
                              ("Stop selected", "stop"), ("Skip", "skip")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, c=choice: self._pick(c))
            if choice == "use":
                btn.setDefault(True)
            row.addWidget(btn)
        lay.addLayout(row)

    @property
    def selected_id(self) -> str:
        rows = self._table.selectionModel().selectedRows()
        return self._ids[rows[0].row()] if rows else (self._ids[0] if self._ids else "")

    def _pick(self, choice: str):
        self.choice = choice
        self.accept()


class PodControl(QWidget):
    server_changed = pyqtSignal()      # pod came up / went away — refresh the mode label
    log = pyqtSignal(str)              # progress lines, echoed into the active run panel

    def __init__(self, config, is_busy: Callable[[], bool], parent=None):
        super().__init__(parent)
        self._config = config
        self._is_busy = is_busy
        self._pod_id = ""              # the pod currently in use (shown in the header)
        self._skip: set[str] = set()   # pods the launch chooser said to leave alone this session
        self._stopped_at_launch: set[str] = set()
        self._owned = False            # did THIS app start it? governs auto-stop only
        self._start_worker: PodStartWorker | None = None
        self._stop_worker: PodStopWorker | None = None
        self._progress: QProgressDialog | None = None
        self._stop_when_idle = False
        self._warned = False
        self._quiet = False             # retry sweeps run without the modal dialog
        self._retry_deadline = 0.0      # epoch seconds; 0 = not retrying
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_tick)

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
        self.log.connect(self._write_log)
        self._refresh_button()

    def _write_log(self, msg: str):
        """Mirror every pod-chain line to a file next to the EXE."""
        path = Path(self._config.get("_base_dir", str(app_dir()))) / POD_LOG
        try:
            if path.exists() and path.stat().st_size > 300_000:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                path.write_text("\n".join(lines[-POD_LOG_MAX_LINES:]) + "\n", encoding="utf-8")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
        except OSError:
            pass

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #

    @property
    def pod_id(self) -> str:
        return self._pod_id

    @property
    def owned(self) -> bool:
        """True only when THIS app started the pod, so only then may it be
        stopped automatically."""
        return self._owned

    def _session_path(self) -> Path:
        return Path(self._config.get("_base_dir", str(app_dir()))) / SESSION_FILE

    def _remember(self, pod_id: str, owned: bool = True, left_running: bool = False):
        self._pod_id = pod_id
        self._owned = owned
        if not owned:
            # Not ours to clean up, so nothing goes in the session file — crash
            # recovery must never offer to stop a pod someone else started.
            return
        try:
            with open(self._session_path(), "w", encoding="utf-8") as f:
                json.dump({"pod_id": pod_id, "left_running": left_running}, f)
        except OSError:
            pass

    def leave_running(self):
        """The exit prompt's "leave it running": mark the session file so the
        next launch knows this was a choice, not a crash, and says so."""
        if self._pod_id and self._owned:
            self._remember(self._pod_id, owned=True, left_running=True)

    def _forget(self):
        self._pod_id = ""
        self._owned = False
        try:
            self._session_path().unlink(missing_ok=True)
        except OSError:
            pass

    def _retrying(self) -> bool:
        return self._retry_deadline > 0

    def _refresh_button(self):
        running = bool(self._pod_id)
        if self._retrying() and not running:
            self._btn.setText("Stop Retrying")
        else:
            self._btn.setText("Stop Pod" if running else "Start Pod")
        self._btn.setEnabled(self._start_worker is None and self._stop_worker is None)
        if not running and not self._retrying():
            self._spend_lbl.setText("")

    # ------------------------------------------------------------------ #
    # Launch
    # ------------------------------------------------------------------ #

    def check_on_launch(self):
        """Pods on launch: show whatever is running — this app's pod from last
        time, or ones started elsewhere (the Chain Automator, the console) —
        with live status, and let the user use one, start another or stop
        one. Only when nothing is up does the plain "start a pod?" prompt run."""
        if not runpod_api.have_key():
            return
        session_id, left_running = self._read_session()
        try:
            pods = runpod_api.list_pods()
        except runpod_api.RunPodError as e:
            self.log.emit(f"RunPod: couldn't list pods ({e})")
            return
        # A pod stopped from the chooser can read RUNNING for a few seconds
        # after the request is accepted; never offer it again this launch.
        running = [p for p in self._running_pods(pods, session_id)
                   if p.get("id") not in self._stopped_at_launch]
        if session_id and session_id not in {p.get("id") for p in running}:
            self._forget()          # the pod this app had is gone — nothing to recover
            session_id = ""
        if running:
            if session_id or self._config.is_runpod():
                self._choose_running(running, session_id, left_running)
                return
            names = ", ".join(p.get("name") or p.get("id", "?") for p in running)
            self.log.emit(f"RunPod: {names} running (started outside the app) — in Local mode, so not used")
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

    def _read_session(self) -> tuple[str, bool]:
        """(pod id this app had last time, whether it was left running on purpose)."""
        try:
            with open(self._session_path(), "r", encoding="utf-8") as f:
                session = json.load(f)
            return (session.get("pod_id") or "").strip(), bool(session.get("left_running"))
        except (OSError, ValueError, AttributeError):
            return "", False

    def _running_pods(self, pods: list[dict], session_id: str) -> list[dict]:
        """Every pod that is up with a GPU — this app's pod first, then the one
        the saved URL names, then the rest. A pod that is RUNNING but hasn't
        reported its GPU yet is waited for (see _settled) rather than skipped."""
        configured = runpod_api.pod_id_from_url(self._config.get("runpod_url", ""))
        rank = {session_id: 0, configured: 1}
        ordered = sorted(pods, key=lambda p: rank.get(p.get("id"), 2))
        running = []
        for pod in ordered:
            if runpod_api.gpu_state(pod) in ("ok", "pending"):
                settled = self._settled(pod)
                if settled is not None:
                    running.append(settled)
        return running

    def _settled(self, pod: dict | None) -> dict | None:
        """The pod if it is (or within RUNTIME_GRACE becomes) healthy, else None.

        RunPod flips a pod to RUNNING a few seconds before the container
        reports in, and until it does the GPU list is missing. A pod that
        was started moments before the app launched would read as unhealthy
        and be skipped — and the launch flow would then offer to start
        ANOTHER pod. So a pending pod is given the same grace the starter
        gives one, with a small cancellable dialog so the UI stays alive."""
        if pod is None:
            return None
        state = runpod_api.gpu_state(pod)
        if state == "ok":
            return pod
        if state != "pending":
            return None
        pod_id = pod.get("id", "")
        name = pod.get("name") or pod_id
        self.log.emit(f"RunPod: {name} is RUNNING but hasn't reported its GPU yet — "
                      f"giving it {runpod_api.RUNTIME_GRACE}s")
        dlg = QProgressDialog(f"{name} is starting — waiting for its GPU to report…",
                              "Skip", 0, 0, self)
        dlg.setWindowTitle("RunPod")
        dlg.setMinimumWidth(460)
        dlg.setMinimumDuration(0)
        dlg.show()
        deadline = time.time() + runpod_api.RUNTIME_GRACE
        next_poll = time.time() + runpod_api.RUNNING_INTERVAL
        try:
            while time.time() < deadline and not dlg.wasCanceled():
                QApplication.processEvents()
                if time.time() < next_poll:
                    time.sleep(0.1)
                    continue
                next_poll = time.time() + runpod_api.RUNNING_INTERVAL
                try:
                    pod = runpod_api.get_pod(pod_id)
                except runpod_api.RunPodError:
                    continue
                state = runpod_api.gpu_state(pod)
                if state == "ok":
                    return pod
                if state != "pending":
                    return None
        finally:
            dlg.close()
        self.log.emit(f"RunPod: {name} never reported a GPU — not using it")
        return None

    def _choose_running(self, running: list[dict], session_id: str, left_running: bool):
        session_pod = next((p for p in running if p.get("id") == session_id), None)
        if session_pod is not None:
            name = session_pod.get("name") or session_id
            opener = (f"You left {name} running when you last quit." if left_running
                      else f"Video Creator didn't shut down cleanly last time and {name} is still running.")
        elif len(running) == 1:
            opener = (f"{running[0].get('name') or running[0].get('id')} is already running "
                      f"— started outside this app (the Chain Automator, the console…).")
        else:
            opener = (f"{len(running)} pods are already running — started outside this app "
                      f"(the Chain Automator, the console…).")
        configured = runpod_api.pod_id_from_url(self._config.get("runpod_url", ""))
        dlg = RunningPodDialog(running, opener, session_id=session_id, configured_id=configured,
                               parent=self)
        dlg.exec()
        choice, pod_id = dlg.choice, dlg.selected_id
        pod = next((p for p in running if p.get("id") == pod_id), None)
        name = (pod or {}).get("name") or pod_id
        if choice == "use" and pod is not None:
            owned = pod_id == session_id
            self._adopt(pod_id, runpod_api.proxy_url(pod_id), owned=owned)
            self.log.emit(
                f"RunPod: using {name}, already running ({runpod_api.spend_summary(pod)})"
                + ("" if owned else " — started outside the app, so it won't be stopped on exit")
                + (f". Connection switched from {configured or 'the previous URL'} to this pod."
                   if pod_id != configured else ""))
        elif choice == "start":
            self._skip = {p.get("id") for p in running}
            self.log.emit(f"RunPod: leaving {', '.join(p.get('name') or p.get('id', '?') for p in running)} "
                          f"to whatever is using it — starting another pod")
            self.start_chain()
        elif choice == "stop" and pod is not None:
            ok = runpod_api.stop_pod(pod_id)
            self.log.emit(f"RunPod: {name} " + ("stopped" if ok else "could NOT be stopped"))
            if not ok:
                QMessageBox.warning(self, "RunPod",
                                    f"Couldn't stop {name}. Stop it in the RunPod console so it "
                                    "doesn't keep billing.")
            if pod_id == session_id:
                self._forget()
            self._stopped_at_launch.add(pod_id)
            self.check_on_launch()      # whatever is still up, or the plain prompt
        else:
            self.log.emit("RunPod: running pod(s) left alone — use the header button to start one")

    # ------------------------------------------------------------------ #
    # Start / stop
    # ------------------------------------------------------------------ #

    def _on_button(self):
        if self._pod_id:
            self.stop_pod()
        elif self._retrying():
            self.cancel_retry("cancelled")
        else:
            self.start_chain()

    def start_chain(self, quiet: bool = False):
        if self._start_worker is not None:
            return
        self._quiet = quiet
        if not runpod_api.have_key():
            QMessageBox.warning(self, "No API key",
                                f"Add your RunPod key to {runpod_api.KEY_FILE_NAME} next to the app.")
            return

        order = list(self._config.get("runpod_pod_order", []) or [])
        gpu_order = list(self._config.get("runpod_gpu_order", []) or [])
        # Pods the launch chooser said to leave alone (in use by another app)
        # stay out of every sweep this session, retries included.
        skip = set(self._skip)
        if not quiet:
            # A retry sweep every 10 minutes must not throw a modal dialog over
            # whatever you're doing, so only the manual path gets one.
            self._progress = QProgressDialog("Looking for an available pod…", "Cancel", 0, 0, self)
            self._progress.setWindowTitle("Starting RunPod")
            self._progress.setMinimumWidth(460)
            self._progress.setMinimumDuration(0)
            self._progress.canceled.connect(self._cancel_start)

        self._start_worker = PodStartWorker(order, gpu_order, skip=skip)
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

    def _adopt(self, pod_id: str, url: str, owned: bool = True):
        """Point the app at this pod and switch to RunPod mode."""
        self._remember(pod_id, owned)
        self._warned = False
        self._stop_when_idle = False
        self._config.set("runpod_url", url)
        self._config.set("mode", "runpod")
        self._config.save()
        self.server_changed.emit()
        self._refresh_button()
        self._poll()

    def _on_ready(self, pod_id: str, url: str):
        was_retrying = self._retrying()
        self._retry_deadline = 0.0
        self._retry_timer.stop()
        self._adopt(pod_id, url)
        self.log.emit(f"RunPod: {pod_id} ready at {url}")
        if was_retrying:
            # You walked away expecting this, so make some noise and come to
            # the front — the pod is billing from now on.
            self._alert()
            win = self.window()
            win.raise_()
            win.activateWindow()

    # ------------------------------------------------------------------ #
    # Keep trying
    # ------------------------------------------------------------------ #

    def _alert(self):
        if not self._config.get("alert_sound_enabled", True):
            return
        alerts.play(self._config.get("alert_sound_path", ""))

    def begin_retry(self):
        window_min = int(self._config.get("runpod_retry_window_min", 120) or 120)
        self._retry_deadline = time.time() + window_min * 60
        self.log.emit(f"RunPod: every pod busy — retrying every "
                      f"{int(self._config.get('runpod_retry_interval_min', 10) or 10)} min "
                      f"until {time.strftime('%H:%M', time.localtime(self._retry_deadline))}")
        self._schedule_next()

    def cancel_retry(self, why: str = ""):
        if not self._retrying():
            return
        self._retry_deadline = 0.0
        self._retry_timer.stop()
        self.log.emit(f"RunPod: stopped retrying{f' ({why})' if why else ''}")
        self._refresh_button()

    def _schedule_next(self):
        remaining = self._retry_deadline - time.time()
        if remaining <= 0:
            self._give_up()
            return
        interval = int(self._config.get("runpod_retry_interval_min", 10) or 10) * 60
        # Don't overshoot the deadline by a whole interval.
        wait = min(interval, remaining)
        self._retry_timer.start(int(wait * 1000))
        nxt = time.strftime("%H:%M", time.localtime(time.time() + wait))
        until = time.strftime("%H:%M", time.localtime(self._retry_deadline))
        self._spend_lbl.setText(
            f"<span style='color:{COLORS['warning']}'>retrying — next {nxt}, until {until}</span>")
        self._refresh_button()

    def _retry_tick(self):
        if not self._retrying():
            return
        if time.time() >= self._retry_deadline:
            self._give_up()
            return
        self.start_chain(quiet=True)

    def _give_up(self):
        self._retry_deadline = 0.0
        self._retry_timer.stop()
        self.log.emit("RunPod: gave up — no pod became available in the retry window")
        self._spend_lbl.setText("")
        self._alert()
        self._refresh_button()

    def _on_exhausted(self, summary: str):
        self._close_progress()

        # Mid-retry this fires every sweep; asking again each time would defeat
        # the point of walking away from the machine.
        if self._retrying():
            self.log.emit("RunPod: still nothing free")
            self._schedule_next()
            return

        interval = int(self._config.get("runpod_retry_interval_min", 10) or 10)
        window = int(self._config.get("runpod_retry_window_min", 120) or 120)
        limit = float(self._config.get("runpod_spend_limit", 0) or 0)
        guard = (f"If one frees up it will start and begin billing while you're away — "
                 f"your ${limit:.2f} spend limit will stop it."
                 if limit > 0 else
                 "WARNING: no spend limit is set, so a pod found while you're away will "
                 "run until you stop it. Set one in Settings first.")

        box = QMessageBox(self)
        box.setWindowTitle("No pods available")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(
            "None of your current pods are available to start.\n\n"
            "This usually means the machines they're pinned to have their GPUs "
            "rented out right now.\n\n"
            f"Keep trying every {interval} min for the next "
            f"{window // 60}h {window % 60:02d}m, and alert you if one frees up?\n\n{guard}")
        if summary:
            # Per-pod reasons, so "nothing available" can be told apart from
            # "every attempt failed for the same unexpected reason".
            box.setDetailedText(summary)
        retry_btn = box.addButton("Keep Trying", QMessageBox.ButtonRole.AcceptRole)
        local_btn = box.addButton("Switch to Local", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(retry_btn)
        box.exec()

        if box.clickedButton() is retry_btn:
            self.begin_retry()
        elif box.clickedButton() is local_btn:
            self._config.set("mode", "local")
            self._config.save()
            self.server_changed.emit()

    def _on_failed(self, msg: str):
        self._close_progress()
        # A Fatal is a key or rate-limit problem: every future sweep would fail
        # the same way, so stop retrying rather than nagging every 10 minutes.
        if self._retrying():
            self.cancel_retry("RunPod returned an error")
            self._alert()
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
        state = runpod_api.gpu_state(pod)
        if state == "pending":
            return                      # RUNNING, GPU report not in yet - next tick
        if state != "ok":
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
            left = runpod_api.projected_runtime(pod, limit)
            summary += (f" / ${limit:.2f}  |  {runpod_api.format_duration(left)} left"
                        if left else f" / ${limit:.2f}  |  limit reached")
        self._spend_lbl.setText(f"<span style='color:{color}'>{summary}</span>")

        rate = runpod_api.hourly_cost(pod)
        tip = [f"{pod.get('name') or self._pod_id}",
               f"${rate:.2f}/hr — ${runpod_api.spend_so_far(pod):.2f} of compute so far",
               "Storage bills separately and is not counted here."]
        if limit > 0:
            left = runpod_api.projected_runtime(pod, limit)
            when = time.strftime("%H:%M", time.localtime(time.time() + left))
            tip.insert(2, f"${limit:.2f} limit reached about {when}"
                          if left else f"${limit:.2f} limit reached")
        self._spend_lbl.setToolTip("\n".join(tip))

        if state == "warn" and not self._warned:
            self._warned = True
            left = runpod_api.projected_runtime(pod, limit)
            self.log.emit(f"RunPod: ${runpod_api.spend_so_far(pod):.2f} of ${limit:.2f} spent — "
                          f"about {runpod_api.format_duration(left)} of GPU time left")
        elif state == "over":
            self._hit_limit(pod)

    def _hit_limit(self, pod: dict):
        if not self._owned:
            # Block new runs, but don't stop a pod the user started themselves —
            # handing their machine back to the pool is not ours to decide.
            if not self._stop_when_idle:
                self._stop_when_idle = True
                self.log.emit(f"RunPod: spend limit reached (${runpod_api.spend_so_far(pod):.2f}). "
                              "No new runs will start. This pod was started outside the app, "
                              "so stop it yourself when you're done.")
            return
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
        self._retry_timer.stop()
        self._retry_deadline = 0.0
        if self._start_worker is not None:
            self._start_worker.cancel()
            self._start_worker.wait(3000)
        if not self._pod_id or not self._owned:
            return          # never stop a pod someone started outside the app
        if not self._config.get("runpod_auto_stop_on_exit", True):
            return
        runpod_api.stop_pod(self._pod_id)
        self._forget()
