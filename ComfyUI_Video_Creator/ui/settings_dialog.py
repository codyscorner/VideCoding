from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget,
)

from config import ConfigManager
from ui.styles import COLORS
from ui.widgets import NoScrollComboBox


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(1240)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Two equal columns so the dialog stays well inside a 1080p screen.
        columns = QHBoxLayout()
        columns.setSpacing(16)
        left_w, right_w = QWidget(), QWidget()
        left, right = QVBoxLayout(left_w), QVBoxLayout(right_w)
        for col in (left, right):
            col.setSpacing(12)
            col.setContentsMargins(0, 0, 0, 0)
        for w in (left_w, right_w):
            w.setMinimumWidth(580)
        columns.addWidget(left_w, stretch=1)
        columns.addWidget(right_w, stretch=1)
        layout.addLayout(columns)

        # ── ComfyUI Server ───────────────────────────────────────────────
        server_group = QGroupBox("ComfyUI Server")
        sl = QVBoxLayout(server_group)
        sl.setSpacing(10)
        mode_row = QHBoxLayout()
        self._local_radio = QRadioButton("Local")
        self._runpod_radio = QRadioButton("RunPod")
        grp = QButtonGroup(self)
        grp.addButton(self._local_radio)
        grp.addButton(self._runpod_radio)
        (self._runpod_radio if config.get("mode", "local") == "runpod" else self._local_radio).setChecked(True)
        mode_row.addWidget(self._local_radio)
        mode_row.addWidget(self._runpod_radio)
        mode_row.addStretch()
        sl.addLayout(mode_row)
        self._local_url = self._text_row(sl, "Local URL:", config.get("comfyui_url", ""), "http://127.0.0.1:8000")
        self._runpod_url = self._text_row(sl, "RunPod URL:", config.get("runpod_url", ""),
                                          "https://xxxxxx-8188.proxy.runpod.net")
        test_row = QHBoxLayout()
        test_row.addStretch()
        test_btn = QPushButton("Test connection")
        test_btn.setObjectName("secondary_btn")
        test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(test_btn)
        sl.addLayout(test_row)
        self._test_status = QLabel("")
        self._test_status.setWordWrap(True)
        self._test_status.setObjectName("status_dim")
        sl.addWidget(self._test_status)
        left.addWidget(server_group)

        # ── Folders ──────────────────────────────────────────────────────
        folders_group = QGroupBox("Folders")
        fl = QVBoxLayout(folders_group)
        fl.setSpacing(10)
        self._image_dir = self._folder_row(fl, "Images:", config.get("image_dir", ""),
                                           "Folder of starting images (Image → Video tab)…")
        self._video_dir = self._folder_row(fl, "Videos:", config.get("video_dir", ""),
                                           "Folder of videos to extend (Video → Extend tab)…")
        self._workflow_dir = self._folder_row(fl, "Workflows:", config.get("workflow_dir", ""),
                                              "Folder of API-format workflow .json files (subfolders included)…")
        self._output_dir = self._folder_row(fl, "Output:", config.get("output_dir", ""),
                                            "Where finished videos are downloaded to…")
        self._loras_dir = self._folder_row(fl, "LoRAs:", config.get("loras_dir", ""),
                                           "ComfyUI models/loras folder — fills the LoRA dropdowns…")
        self._library_dir = self._folder_row(fl, "Library:", config.get("library_dir", ""),
                                             "Folder shown on the Library tab (blank = the Output folder)…")
        self._archive_dir = self._folder_row(fl, "Archive:", config.get("archive_dir", ""),
                                             "Where archived videos are moved to (watch later in Desktop Video Browser)…")
        left.addWidget(folders_group)

        # ── Staging ──────────────────────────────────────────────────────
        stage_group = QGroupBox("Folder-loader workflows (Load Image List From Dir)")
        stl = QVBoxLayout(stage_group)
        stl.setSpacing(10)
        note = QLabel("Batch-style workflows read a whole folder instead of one LoadImage node. "
                      "The selected image is staged alone into a run folder here and the loader is pointed at it.")
        note.setWordWrap(True)
        note.setObjectName("status_dim")
        stl.addWidget(note)
        self._staging_dir = self._folder_row(stl, "Local staging:", config.get("staging_dir_local", ""),
                                             "Local folder for staged images (blank = app's temp folder)…")
        self._runpod_input = self._text_row(stl, "RunPod input:", config.get("runpod_input_dir", ""),
                                            "Absolute path of ComfyUI's input folder on the pod…")
        right.addWidget(stage_group)

        # ── FFmpeg ───────────────────────────────────────────────────────
        ff_group = QGroupBox("FFmpeg")
        ffl = QVBoxLayout(ff_group)
        ffl.setSpacing(10)
        self._ffmpeg = self._file_row(ffl, "FFmpeg path:", config.get("ffmpeg_path", ""),
                                      "Blank = ffmpeg.exe next to the app, then PATH…")
        ff_note = QLabel("Used for video thumbnails, last-frame extraction and appending the new clip to the source video.")
        ff_note.setWordWrap(True)
        ff_note.setObjectName("status_dim")
        ffl.addWidget(ff_note)
        right.addWidget(ff_group)

        # ── Editor ───────────────────────────────────────────────────────
        ed_group = QGroupBox("Prompt editor")
        edl = QHBoxLayout(ed_group)
        edl.addWidget(QLabel("Text size:"))
        self._font_spin = QSpinBox()
        self._font_spin.setRange(7, 20)
        self._font_spin.setValue(int(config.get("prompt_font_size", 10) or 10))
        edl.addWidget(self._font_spin)
        edl.addStretch()
        right.addWidget(ed_group)

        # ── AI Prompt Rewriter ──────────────────────────────────────────
        rw_group = QGroupBox("AI Prompt Rewriter (local LM Studio)")
        rwl = QVBoxLayout(rw_group)
        rwl.setSpacing(10)
        rw_note = QLabel("Turns a rough scene idea into a correctly-formatted MiniMax H3 prompt "
                          "using any model already loaded in LM Studio - nothing is uploaded anywhere.")
        rw_note.setWordWrap(True)
        rw_note.setObjectName("status_dim")
        rwl.addWidget(rw_note)
        self._rewriter_url = self._text_row(rwl, "LM Studio URL:", config.get("rewriter_base_url", ""),
                                            "http://127.0.0.1:1234/v1")
        model_row = QHBoxLayout()
        model_row.addWidget(self._label("Model:"))
        self._rewriter_model = NoScrollComboBox()
        self._rewriter_model.setEditable(True)
        saved_model = config.get("rewriter_model", "")
        if saved_model:
            self._rewriter_model.addItem(saved_model)
        model_row.addWidget(self._rewriter_model, stretch=1)
        fetch_btn = QPushButton("Fetch models")
        fetch_btn.setObjectName("secondary_btn")
        fetch_btn.clicked.connect(self._fetch_rewriter_models)
        model_row.addWidget(fetch_btn)
        rwl.addLayout(model_row)
        self._rewriter_status = QLabel("")
        self._rewriter_status.setWordWrap(True)
        self._rewriter_status.setObjectName("status_dim")
        rwl.addWidget(self._rewriter_status)
        right.addWidget(rw_group)

        # ── RunPod pod control ───────────────────────────────────────────
        pod_group = QGroupBox("RunPod pod control")
        pl = QVBoxLayout(pod_group)
        pl.setSpacing(10)

        list_row = QHBoxLayout()
        self._pod_list = QListWidget()
        # Fixed, not minimum: QListWidget asks for 256px by default, which
        # over-commits the column and makes Qt overlap the rows below it.
        self._pod_list.setFixedHeight(92)
        self._pod_list.setToolTip("Tried top to bottom; the first available pod is used.\n"
                                  "Existing pods only — never created or terminated.\n"
                                  "Double-click a pod to point the RunPod URL at it.")
        self._pod_list.itemDoubleClicked.connect(self._use_pod)
        list_row.addWidget(self._pod_list, stretch=1)
        btn_col = QVBoxLayout()
        for text, slot in (("▲", lambda: self._move_pod(-1)), ("▼", lambda: self._move_pod(1))):
            b = QPushButton(text)
            b.setObjectName("small_btn")
            b.setFixedWidth(40)
            b.clicked.connect(slot)
            btn_col.addWidget(b)
        refresh_btn = QPushButton("↻")
        refresh_btn.setObjectName("small_btn")
        refresh_btn.setFixedWidth(40)
        refresh_btn.setToolTip("Fetch the pod list from RunPod")
        refresh_btn.clicked.connect(self._refresh_pods)
        btn_col.addWidget(refresh_btn)
        btn_col.addStretch()
        list_row.addLayout(btn_col)
        pl.addLayout(list_row)

        limit_row = QHBoxLayout()
        limit_row.addWidget(self._label("Spend limit:"))
        self._spend_limit = QDoubleSpinBox()
        self._spend_limit.setRange(0.0, 10000.0)
        self._spend_limit.setDecimals(2)
        self._spend_limit.setPrefix("$ ")
        self._spend_limit.setSpecialValueText("off")
        self._spend_limit.setValue(float(config.get("runpod_spend_limit", 0) or 0))
        limit_row.addWidget(self._spend_limit)
        limit_row.addWidget(QLabel("per pod run — 0 = off"))
        limit_row.addStretch()
        pl.addLayout(limit_row)

        # As a tooltip rather than a label: the right column is full at 1080p,
        # and a wrapped note here pushes the group past its allocation.
        self._spend_limit.setToolTip(
            "Compute only — storage bills separately.\n"
            "A safety net, not a hard cap: it can only act while the app is running, "
            "so a crash or reboot leaves the pod up.")

        self._pod_prompt = QCheckBox("Ask on launch")
        self._pod_prompt.setToolTip("Offer to start a pod each time the app opens")
        self._pod_prompt.setChecked(bool(config.get("runpod_auto_prompt", True)))
        self._pod_autostop = QCheckBox("Stop pod on exit")
        self._pod_autostop.setToolTip("Stop the pod this app started when quitting")
        self._pod_autostop.setChecked(bool(config.get("runpod_auto_stop_on_exit", True)))
        checks = QHBoxLayout()
        checks.addWidget(self._pod_prompt)
        checks.addWidget(self._pod_autostop)
        checks.addStretch()
        pl.addLayout(checks)

        pod_test_row = QHBoxLayout()
        pod_test_row.addStretch()
        pod_test_btn = QPushButton("Test API key")
        pod_test_btn.setObjectName("secondary_btn")
        pod_test_btn.clicked.connect(self._test_runpod_api)
        pod_test_row.addWidget(pod_test_btn)
        pl.addLayout(pod_test_row)
        self._pod_status = QLabel("")
        self._pod_status.setWordWrap(True)
        self._pod_status.setObjectName("status_dim")
        pl.addWidget(self._pod_status)
        # Left column: Server + Folders leave ~440px free there, while the
        # right column already runs to the bottom of the dialog.
        left.addWidget(pod_group)
        self._load_pod_order()

        left.addStretch()
        right.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedWidth(110)
        return lbl

    def _text_row(self, parent, label, value, placeholder) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(self._label(label))
        edit = QLineEdit(value or "")
        edit.setPlaceholderText(placeholder)
        row.addWidget(edit, stretch=1)
        parent.addLayout(row)
        return edit

    def _folder_row(self, parent, label, value, placeholder) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(self._label(label))
        edit = QLineEdit(value or "")
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("…")
        btn.setObjectName("small_btn")
        btn.setFixedWidth(40)
        btn.clicked.connect(lambda: self._browse_folder(edit))
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent.addLayout(row)
        return edit

    def _file_row(self, parent, label, value, placeholder) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(self._label(label))
        edit = QLineEdit(value or "")
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("…")
        btn.setObjectName("small_btn")
        btn.setFixedWidth(40)
        btn.clicked.connect(lambda: self._browse_file(edit))
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent.addLayout(row)
        return edit

    def _browse_folder(self, edit: QLineEdit):
        current = edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", current or str(Path.home()))
        if folder:
            edit.setText(folder)

    def _browse_file(self, edit: QLineEdit):
        current = edit.text().strip()
        path, _ = QFileDialog.getOpenFileName(self, "Select ffmpeg.exe", current or str(Path.home()),
                                              "Executables (*.exe);;All Files (*)")
        if path:
            edit.setText(path)

    def _fetch_rewriter_models(self):
        import prompt_rewriter as pr
        url = self._rewriter_url.text().strip()
        if not url:
            self._rewriter_status.setText("Enter the LM Studio URL first.")
            return
        self._rewriter_status.setText(f"Fetching models from {url} …")
        self._rewriter_status.repaint()
        try:
            models = pr.list_models(url)
        except pr.RewriterError as e:
            self._rewriter_status.setText(str(e))
            self._rewriter_status.setStyleSheet(f"color: {COLORS['error']};")
            return
        current = self._rewriter_model.currentText().strip()
        self._rewriter_model.clear()
        self._rewriter_model.addItems(models)
        if current:
            idx = self._rewriter_model.findText(current)
            if idx >= 0:
                self._rewriter_model.setCurrentIndex(idx)
            else:
                self._rewriter_model.setEditText(current)
        self._rewriter_status.setText(f"Found {len(models)} model(s).")
        self._rewriter_status.setStyleSheet(f"color: {COLORS['success']};")

    # ── RunPod pod control ───────────────────────────────────────────────

    def _load_pod_order(self):
        """Show the saved order straight away; names arrive with Refresh."""
        self._pod_list.clear()
        for pod_id in (self._config.get("runpod_pod_order", []) or []):
            item = QListWidgetItem(pod_id)
            item.setData(Qt.ItemDataRole.UserRole, pod_id)
            self._pod_list.addItem(item)

    def _use_pod(self, item):
        """Double-click: point the connection at this pod.

        The proxy URL is derived from the pod id and is stable for the life of
        the pod, so this needs no network call — it just fills in the RunPod URL
        and switches the mode across. Whether the pod is actually running is a
        separate question; Test connection answers that.
        """
        import runpod_api
        pod_id = item.data(Qt.ItemDataRole.UserRole)
        if not pod_id:
            return
        url = runpod_api.proxy_url(pod_id)
        self._runpod_url.setText(url)
        self._runpod_radio.setChecked(True)
        self._pod_status.setText(f"RunPod URL set to {pod_id}. Save to apply.")
        self._pod_status.setStyleSheet(f"color: {COLORS['success']};")

    def _move_pod(self, delta: int):
        row = self._pod_list.currentRow()
        new = row + delta
        if row < 0 or not (0 <= new < self._pod_list.count()):
            return
        self._pod_list.insertItem(new, self._pod_list.takeItem(row))
        self._pod_list.setCurrentRow(new)

    def _refresh_pods(self):
        """Fetch the account's pods, keeping whatever order is already set and
        appending anything new at the bottom."""
        import runpod_api
        self._pod_status.setText("Fetching pods…")
        self._pod_status.setStyleSheet(f"color: {COLORS['fg_dim']};")
        self._pod_status.repaint()
        try:
            pods = {p.get("id"): p for p in runpod_api.list_pods()}
        except runpod_api.RunPodError as e:
            self._pod_status.setText(str(e))
            self._pod_status.setStyleSheet(f"color: {COLORS['error']};")
            return
        except Exception as e:  # noqa: BLE001
            self._pod_status.setText(f"{type(e).__name__}: {e}")
            self._pod_status.setStyleSheet(f"color: {COLORS['error']};")
            return

        existing = [self._pod_list.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self._pod_list.count())]
        ordered = [pid for pid in existing if pid in pods]
        ordered += [pid for pid in pods if pid not in ordered]

        self._pod_list.clear()
        for pid in ordered:
            item = QListWidgetItem(runpod_api.describe(pods[pid]))
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self._pod_list.addItem(item)
        self._pod_status.setText(f"{len(ordered)} pod(s). Order them best first.")
        self._pod_status.setStyleSheet(f"color: {COLORS['success']};")

    def _test_runpod_api(self):
        import runpod_api
        self._pod_status.setText("Checking RunPod…")
        self._pod_status.setStyleSheet(f"color: {COLORS['fg_dim']};")
        self._pod_status.repaint()
        ok, msg = runpod_api.test_connection()
        self._pod_status.setText(msg)
        self._pod_status.setStyleSheet(f"color: {COLORS['success' if ok else 'error']};")

    def _test_connection(self):
        from comfy_client import ComfyClient
        url = (self._runpod_url if self._runpod_radio.isChecked() else self._local_url).text().strip()
        if not url:
            self._test_status.setText("Enter a URL for the selected mode first.")
            return
        self._test_status.setText(f"Connecting to {url} …")
        self._test_status.repaint()
        try:
            stats = ComfyClient(url).test()
            sysinfo = stats.get("system", {}) or {}
            devs = stats.get("devices", []) or []
            gpu = devs[0].get("name", "") if devs else "no GPU reported"
            vram = devs[0].get("vram_total", 0) // (1024 ** 3) if devs else 0
            self._test_status.setText(
                f"OK — ComfyUI {sysinfo.get('comfyui_version', '')} · {gpu}"
                + (f" ({vram} GB)" if vram else ""))
            self._test_status.setStyleSheet(f"color: {COLORS['success']};")
        except Exception as e:  # noqa: BLE001
            self._test_status.setText(f"Failed: {type(e).__name__}: {e}")
            self._test_status.setStyleSheet(f"color: {COLORS['error']};")

    def _save(self):
        c = self._config
        c.set("mode", "runpod" if self._runpod_radio.isChecked() else "local")
        c.set("comfyui_url", self._local_url.text().strip())
        c.set("runpod_url", self._runpod_url.text().strip())
        c.set("image_dir", self._image_dir.text().strip())
        c.set("video_dir", self._video_dir.text().strip())
        c.set("workflow_dir", self._workflow_dir.text().strip())
        c.set("output_dir", self._output_dir.text().strip())
        c.set("loras_dir", self._loras_dir.text().strip())
        c.set("library_dir", self._library_dir.text().strip())
        c.set("archive_dir", self._archive_dir.text().strip())
        c.set("staging_dir_local", self._staging_dir.text().strip())
        c.set("runpod_input_dir", self._runpod_input.text().strip())
        c.set("ffmpeg_path", self._ffmpeg.text().strip())
        c.set("prompt_font_size", int(self._font_spin.value()))
        c.set("rewriter_base_url", self._rewriter_url.text().strip())
        c.set("rewriter_model", self._rewriter_model.currentText().strip())
        c.set("runpod_pod_order", [self._pod_list.item(i).data(Qt.ItemDataRole.UserRole)
                                   for i in range(self._pod_list.count())])
        c.set("runpod_spend_limit", float(self._spend_limit.value()))
        c.set("runpod_auto_prompt", bool(self._pod_prompt.isChecked()))
        c.set("runpod_auto_stop_on_exit", bool(self._pod_autostop.isChecked()))
        c.save()
        self.accept()
