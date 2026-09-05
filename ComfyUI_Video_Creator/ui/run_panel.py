"""Right-hand panel of each tab: workflow picker, prompt/seed/length
editing, run controls, progress, log and results."""

from __future__ import annotations

import os
import random
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
    QSizePolicy, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from config import ConfigManager
from run_worker import RunRequest
from ui.styles import COLORS
from workflow_tools import (
    Analysis, WorkflowError, analyze, apply_prompts, apply_value,
    list_workflows, load_workflow, save_workflow,
)

VIDEO_INPUT_MODES = [
    ("auto", "Auto (video node if the workflow has one, else last frame)"),
    ("last_frame", "Last frame → image input (LoadImage)"),
    ("upload_video", "Upload whole video → video input (LoadVideo)"),
]

MAX_LOG_LINES = 600


class RunPanel(QWidget):
    run_requested = pyqtSignal(object)      # RunRequest
    cancel_requested = pyqtSignal()
    play_requested = pyqtSignal(str)

    def __init__(self, kind: str, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.kind = kind                    # "image" | "video"
        self._cfg = config
        self._source: Path | None = None
        self._workflow_path: Path | None = None
        self._workflow_rel = ""
        self._analysis: Analysis | None = None
        self._prompt_edits: list[tuple[object, QTextEdit]] = []   # (PromptField, editor)
        self._running = False
        self._run_started = 0.0
        self._results: list[str] = []
        # progress bookkeeping
        self._sampler_total = 0
        self._phases_total = 0
        self._phases_seen = 0
        self._offset = 0
        self._last_value = 0
        self._last_max = 0

        self.setMinimumWidth(540)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── Workflow ────────────────────────────────────────────────────
        wf_group = QGroupBox("Workflow")
        wf_layout = QVBoxLayout(wf_group)
        wf_layout.setSpacing(6)
        row = QHBoxLayout()
        self._wf_combo = QComboBox()
        self._wf_combo.setMinimumWidth(300)
        self._wf_combo.currentIndexChanged.connect(self._on_workflow_changed)
        row.addWidget(self._wf_combo, stretch=1)
        refresh = QPushButton("↻")
        refresh.setObjectName("small_btn")
        refresh.setFixedWidth(36)
        refresh.setToolTip("Rescan the workflow folder")
        refresh.clicked.connect(self.reload_workflows)
        row.addWidget(refresh)
        wf_layout.addLayout(row)
        self._wf_status = QLabel("")
        self._wf_status.setObjectName("status_dim")
        self._wf_status.setWordWrap(True)
        wf_layout.addWidget(self._wf_status)
        root.addWidget(wf_group)

        # ── Prompts ─────────────────────────────────────────────────────
        self._prompt_group = QGroupBox("Prompts")
        pg = QVBoxLayout(self._prompt_group)
        pg.setSpacing(6)
        self._prompt_box = QVBoxLayout()
        self._prompt_box.setSpacing(4)
        pg.addLayout(self._prompt_box)
        prow = QHBoxLayout()
        prow.addStretch()
        self._prompt_font_lbl = QLabel("Text size:")
        prow.addWidget(self._prompt_font_lbl)
        self._font_spin = QSpinBox()
        self._font_spin.setRange(7, 20)
        self._font_spin.setValue(int(config.get("prompt_font_size", 10) or 10))
        self._font_spin.setFixedWidth(60)
        self._font_spin.valueChanged.connect(self._apply_font_size)
        prow.addWidget(self._font_spin)
        self._reload_btn = QPushButton("↺ Reload")
        self._reload_btn.setObjectName("secondary_btn")
        self._reload_btn.setToolTip("Discard edits and reload the prompts from the workflow file")
        self._reload_btn.clicked.connect(self._reload_workflow)
        prow.addWidget(self._reload_btn)
        self._save_btn = QPushButton("💾 Save to workflow")
        self._save_btn.setObjectName("secondary_btn")
        self._save_btn.setToolTip("Write the prompts and length shown here back into the workflow JSON")
        self._save_btn.clicked.connect(self._save_to_workflow)
        prow.addWidget(self._save_btn)
        pg.addLayout(prow)
        root.addWidget(self._prompt_group, stretch=2)

        # ── Options ─────────────────────────────────────────────────────
        opt_group = QGroupBox("Options")
        og = QVBoxLayout(opt_group)
        og.setSpacing(6)

        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel("Seed:"))
        self._seed_mode = QComboBox()
        self._seed_mode.addItems(["Random", "Fixed"])
        self._seed_mode.setFixedWidth(96)
        self._seed_mode.setToolTip("Random: a new seed every run. Fixed: use the seed on the right.")
        self._seed_mode.setCurrentIndex(1 if config.get("seed_mode", "random") == "fixed" else 0)
        self._seed_mode.currentIndexChanged.connect(self._on_seed_mode)
        seed_row.addWidget(self._seed_mode)
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 2_147_483_647)
        self._seed_spin.setValue(int(config.get("seed_value", 0) or 0))
        self._seed_spin.setMinimumWidth(140)
        self._seed_spin.valueChanged.connect(lambda v: self._cfg.set("seed_value", int(v)))
        seed_row.addWidget(self._seed_spin)
        dice = QPushButton("🎲")
        dice.setObjectName("small_btn")
        dice.setFixedWidth(40)
        dice.setToolTip("Pick a new fixed seed")
        dice.clicked.connect(lambda: self._seed_spin.setValue(random.randint(0, 2_147_483_647)))
        seed_row.addWidget(dice)
        seed_row.addStretch()
        self._length_lbl = QLabel("Length:")
        seed_row.addWidget(self._length_lbl)
        self._length_spin = QDoubleSpinBox()
        self._length_spin.setMinimumWidth(110)
        seed_row.addWidget(self._length_spin)
        og.addLayout(seed_row)
        self._on_seed_mode()

        if kind == "video":
            mode_row = QHBoxLayout()
            mode_row.addWidget(QLabel("Video input:"))
            self._input_mode = QComboBox()
            for key, label in VIDEO_INPUT_MODES:
                self._input_mode.addItem(label, key)
            current = config.get("video_input_mode", "auto")
            for i, (key, _) in enumerate(VIDEO_INPUT_MODES):
                if key == current:
                    self._input_mode.setCurrentIndex(i)
            self._input_mode.currentIndexChanged.connect(
                lambda _i: self._cfg.set("video_input_mode", self._input_mode.currentData()))
            mode_row.addWidget(self._input_mode, stretch=1)
            og.addLayout(mode_row)
            self._stitch_chk = QCheckBox("Append the new clip to the source video (saves <name>_extended.mp4 as well)")
            self._stitch_chk.setChecked(bool(config.get("extend_stitch", True)))
            self._stitch_chk.toggled.connect(lambda v: self._cfg.set("extend_stitch", bool(v)))
            og.addWidget(self._stitch_chk)
        else:
            self._input_mode = None
            self._stitch_chk = None
        root.addWidget(opt_group)

        # ── Run controls ────────────────────────────────────────────────
        run_row = QHBoxLayout()
        self._source_lbl = QLabel("No image selected" if kind == "image" else "No video selected")
        self._source_lbl.setObjectName("status_dim")
        self._source_lbl.setWordWrap(True)
        run_row.addWidget(self._source_lbl, stretch=1)
        self._run_btn = QPushButton("▶  Create Video" if kind == "image" else "▶  Extend Video")
        self._run_btn.setObjectName("run_btn")
        self._run_btn.clicked.connect(self._on_run)
        run_row.addWidget(self._run_btn)
        self._cancel_btn = QPushButton("✕ Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        run_row.addWidget(self._cancel_btn)
        root.addLayout(run_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("")
        root.addWidget(self._progress)
        self._progress_lbl = QLabel("Idle")
        self._progress_lbl.setObjectName("status_dim")
        root.addWidget(self._progress_lbl)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick)

        # ── Log ─────────────────────────────────────────────────────────
        self._log = QListWidget()
        self._log.setMinimumHeight(60)
        self._log.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        root.addWidget(self._log, stretch=1)

        # ── Results ─────────────────────────────────────────────────────
        res_group = QGroupBox("Results")
        rg = QVBoxLayout(res_group)
        rg.setSpacing(6)
        self._results_list = QListWidget()
        self._results_list.setMaximumHeight(64)
        self._results_list.itemDoubleClicked.connect(lambda it: self.play_requested.emit(it.data(Qt.ItemDataRole.UserRole)))
        rg.addWidget(self._results_list)
        rrow = QHBoxLayout()
        play_btn = QPushButton("▶ Play")
        play_btn.setObjectName("secondary_btn")
        play_btn.clicked.connect(self._play_selected)
        rrow.addWidget(play_btn)
        open_btn = QPushButton("📂 Open Folder")
        open_btn.setObjectName("secondary_btn")
        open_btn.clicked.connect(self._open_result_folder)
        rrow.addWidget(open_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary_btn")
        clear_btn.clicked.connect(self._results_list.clear)
        rrow.addWidget(clear_btn)
        rrow.addStretch()
        rg.addLayout(rrow)
        root.addWidget(res_group)

        self.reload_workflows()
        self._update_run_enabled()

    # ------------------------------------------------------------------ #
    # Workflows
    # ------------------------------------------------------------------ #

    def _config_key(self) -> str:
        return "image_workflow" if self.kind == "image" else "video_workflow"

    def reload_workflows(self):
        wf_dir = Path((self._cfg.get("workflow_dir", "") or "").strip())
        rels = list_workflows(wf_dir) if str(wf_dir) else []
        remembered = self._cfg.get(self._config_key(), "") or self._workflow_rel
        self._wf_combo.blockSignals(True)
        self._wf_combo.clear()
        for rel in rels:
            self._wf_combo.addItem(rel, rel)
        self._wf_combo.blockSignals(False)
        if not rels:
            self._workflow_path = None
            self._analysis = None
            self._set_wf_status(
                "No workflow JSON files found — set the Workflows folder in Settings." if not wf_dir.is_dir()
                else f"No .json workflows in {wf_dir}", ok=False)
            self._rebuild_prompts()
            self._update_run_enabled()
            return
        idx = self._wf_combo.findData(remembered) if remembered else -1
        self._wf_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._on_workflow_changed(self._wf_combo.currentIndex())

    def _on_workflow_changed(self, _idx: int):
        rel = self._wf_combo.currentData()
        if not rel:
            return
        self._workflow_rel = rel
        self._cfg.set(self._config_key(), rel)
        self._workflow_path = Path(self._cfg.get("workflow_dir", "")) / rel
        self._load_analysis()

    def _reload_workflow(self):
        if self._workflow_path is not None:
            self._load_analysis()

    def _load_analysis(self):
        try:
            wf = load_workflow(self._workflow_path)
            self._analysis = analyze(wf)
        except WorkflowError as e:
            self._analysis = None
            self._set_wf_status(str(e), ok=False)
            self._rebuild_prompts()
            self._update_run_enabled()
            return
        a = self._analysis
        problems = []
        if self.kind == "image" and not a.accepts_image:
            problems.append("no image input node (LoadImage) — pick an image-to-video workflow")
        if self.kind == "video" and not (a.accepts_image or a.accepts_video):
            problems.append("no video or image input node")
        if not a.output_nodes:
            problems.append("no SaveVideo / VHS_VideoCombine node — nothing will be downloaded")
        if problems:
            self._set_wf_status("⚠ " + "; ".join(problems) + f"\n{a.describe()}", ok=False)
        else:
            self._set_wf_status("✓ " + a.describe(), ok=True)
        self._rebuild_prompts()
        self._update_run_enabled()

    def _set_wf_status(self, text: str, ok: bool):
        self._wf_status.setObjectName("status_ok" if ok else "status_err")
        self._wf_status.setStyleSheet("")   # force re-polish for the new objectName
        self._wf_status.setText(text)

    # ------------------------------------------------------------------ #
    # Prompts / length
    # ------------------------------------------------------------------ #

    def _rebuild_prompts(self):
        while self._prompt_box.count():
            item = self._prompt_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._prompt_edits = []
        a = self._analysis
        if a is None or not a.prompts:
            lbl = QLabel("This workflow exposes no editable prompt text." if a is not None else "")
            lbl.setObjectName("status_dim")
            self._prompt_box.addWidget(lbl)
        else:
            single_h3 = len(a.prompts) == 1 and a.prompts[0].key == "prompt"
            for pf in a.prompts:
                lbl = QLabel(pf.label)
                lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-weight: bold;")
                self._prompt_box.addWidget(lbl)
                edit = QTextEdit()
                edit.setAcceptRichText(False)
                edit.setPlainText(pf.text)
                # Shrinkable so a tall prompt stack can't push the log and
                # results off a 1080p screen; grows back when there's room.
                if single_h3:
                    lo, hi, stretch = 90, 260, 2
                elif pf.negative:
                    lo, hi, stretch = 40, 70, 1
                else:
                    lo, hi, stretch = 60, 130, 2
                edit.setMinimumHeight(lo)
                edit.setMaximumHeight(hi)
                edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self._prompt_box.addWidget(edit, stretch=stretch)
                self._prompt_edits.append((pf, edit))
        self._apply_font_size(self._font_spin.value())

        # Length / duration control
        fld = a.length_field if a is not None else None
        visible = fld is not None
        self._length_lbl.setVisible(visible)
        self._length_spin.setVisible(visible)
        if fld is not None:
            self._length_lbl.setText(fld.label + ":")
            self._length_spin.blockSignals(True)
            if fld.kind == "int":
                self._length_spin.setDecimals(0)
                self._length_spin.setRange(1, 100000)
                self._length_spin.setSingleStep(1)
            else:
                self._length_spin.setDecimals(1)
                self._length_spin.setRange(0.1, 600.0)
                self._length_spin.setSingleStep(0.5)
            self._length_spin.setValue(fld.value)
            self._length_spin.blockSignals(False)

    def _apply_font_size(self, size: int):
        self._cfg.set("prompt_font_size", int(size))
        font = QFont("Segoe UI", int(size))
        for _pf, edit in self._prompt_edits:
            edit.setFont(font)

    def _prompt_overrides(self) -> dict[tuple[str, str], str]:
        return {(pf.node_id, pf.key): edit.toPlainText() for pf, edit in self._prompt_edits}

    def _save_to_workflow(self):
        if self._workflow_path is None or self._analysis is None:
            return
        try:
            wf = load_workflow(self._workflow_path)
            apply_prompts(wf, self._prompt_overrides())
            if self._analysis.length_field is not None:
                apply_value(wf, self._analysis.length_field, self._length_spin.value())
            save_workflow(self._workflow_path, wf)
            self.append_log(f"Saved prompts to {self._workflow_path.name}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))

    # ------------------------------------------------------------------ #
    # Seed
    # ------------------------------------------------------------------ #

    def _on_seed_mode(self, *_):
        fixed = self._seed_mode.currentIndex() == 1
        self._seed_spin.setEnabled(fixed)
        self._cfg.set("seed_mode", "fixed" if fixed else "random")

    # ------------------------------------------------------------------ #
    # Source / run
    # ------------------------------------------------------------------ #

    def set_source(self, path: Path | None):
        self._source = path
        if path is None:
            self._source_lbl.setText("No image selected" if self.kind == "image" else "No video selected")
        else:
            self._source_lbl.setText(f"Selected: {path.name}")
        self._update_run_enabled()

    def _update_run_enabled(self):
        ok = (not self._running and self._source is not None
              and self._workflow_path is not None and self._analysis is not None)
        if ok and self.kind == "image":
            ok = self._analysis.accepts_image
        if ok and self.kind == "video":
            ok = self._analysis.accepts_image or self._analysis.accepts_video
        self._run_btn.setEnabled(bool(ok))

    def _on_run(self):
        if self._source is None or self._workflow_path is None or self._analysis is None:
            return
        rel = Path(self._workflow_rel)
        label = rel.parts[0] if len(rel.parts) > 1 else rel.stem
        seed = int(self._seed_spin.value()) if self._seed_mode.currentIndex() == 1 else None
        fld = self._analysis.length_field
        req = RunRequest(
            workflow_path=self._workflow_path,
            workflow_label=label,
            source_path=self._source,
            source_kind=self.kind,
            prompts=self._prompt_overrides(),
            seed=seed,
            length_field=fld,
            length_value=float(self._length_spin.value()) if fld is not None else None,
            video_input_mode=self._input_mode.currentData() if self._input_mode is not None else "auto",
            extend_stitch=bool(self._stitch_chk.isChecked()) if self._stitch_chk is not None else False,
        )
        self.run_requested.emit(req)

    def set_running(self, running: bool, active: bool = True):
        """running: a job is in progress somewhere; active: this panel owns it."""
        self._running = running
        self._cancel_btn.setEnabled(running and active)
        self._update_run_enabled()
        if running and active:
            self._log.clear()
            self._progress.setRange(0, 0)
            self._progress.setFormat("")
            self._progress_lbl.setText("Starting…")
            self._run_started = time.time()
            self._sampler_total = self._phases_total = self._phases_seen = 0
            self._offset = self._last_value = self._last_max = 0
            self._elapsed_timer.start()
        elif not running:
            self._elapsed_timer.stop()

    # ------------------------------------------------------------------ #
    # Worker feedback
    # ------------------------------------------------------------------ #

    def append_log(self, message: str):
        self._log.addItem(QListWidgetItem(f"[{time.strftime('%H:%M:%S')}] {message}"))
        while self._log.count() > MAX_LOG_LINES:
            self._log.takeItem(0)
        self._log.scrollToBottom()

    def on_plan(self, total_steps: int, phases: int):
        self._sampler_total = max(0, total_steps)
        self._phases_total = max(0, phases)
        self._phases_seen = 0
        self._offset = self._last_value = self._last_max = 0
        total = self._sampler_total + self._phases_total
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(0)
            self._progress.setFormat("%p%")
        else:
            self._progress.setRange(0, 0)

    def on_step(self, value: int, vmax: int):
        if value < self._last_value:
            self._offset += self._last_max
        self._last_value, self._last_max = value, vmax
        cum = min(self._offset + value, self._sampler_total) if self._sampler_total else self._offset + value
        if self._progress.maximum() > 0:
            self._progress.setValue(cum)
        shown_total = self._sampler_total or vmax
        self._progress_lbl.setText(f"Step {cum}/{shown_total} · {self._elapsed()}")

    def on_phase(self, label: str):
        self._phases_seen += 1
        if self._progress.maximum() > 0:
            self._progress.setValue(min(self._sampler_total + self._phases_seen - 1, self._progress.maximum()))
        self._progress_lbl.setText(f"{label} · {self._elapsed()}")

    def on_done(self, paths: list[str]):
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._progress.setFormat("Done")
        self._progress_lbl.setText(f"Finished in {self._elapsed()}")
        for p in paths:
            item = QListWidgetItem(Path(p).name)
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self._results_list.addItem(item)
            self._results.append(p)
        if paths:
            self._results_list.setCurrentRow(self._results_list.count() - 1)

    def on_failed(self, message: str):
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setFormat("")
        self._progress_lbl.setText(("Cancelled" if message == "Cancelled" else "Failed") + f" after {self._elapsed()}")
        self.append_log(("✕ " + message) if message != "Cancelled" else "Cancelled by user")

    def _tick(self):
        text = self._progress_lbl.text()
        if "·" in text:
            head = text.split("·", 1)[0].strip()
            self._progress_lbl.setText(f"{head} · {self._elapsed()}")
        else:
            self._progress_lbl.setText(f"{text.split(' (', 1)[0]} ({self._elapsed()})")

    def _elapsed(self) -> str:
        m, s = divmod(int(time.time() - self._run_started), 60)
        return f"{m:02d}m {s:02d}s"

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #

    def _selected_result(self) -> str | None:
        items = self._results_list.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        if self._results_list.count():
            return self._results_list.item(self._results_list.count() - 1).data(Qt.ItemDataRole.UserRole)
        return None

    def _play_selected(self):
        p = self._selected_result()
        if p:
            self.play_requested.emit(p)

    def _open_result_folder(self):
        p = self._selected_result()
        folder = Path(p).parent if p else Path((self._cfg.get("output_dir", "") or "").strip())
        if folder and folder.is_dir():
            os.startfile(str(folder))
