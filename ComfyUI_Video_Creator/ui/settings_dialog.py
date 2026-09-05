from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget,
)

from config import ConfigManager
from ui.styles import COLORS


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
        c.set("staging_dir_local", self._staging_dir.text().strip())
        c.set("runpod_input_dir", self._runpod_input.text().strip())
        c.set("ffmpeg_path", self._ffmpeg.text().strip())
        c.set("prompt_font_size", int(self._font_spin.value()))
        c.save()
        self.accept()
