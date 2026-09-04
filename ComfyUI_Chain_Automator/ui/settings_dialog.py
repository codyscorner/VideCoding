from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QDialogButtonBox, QCheckBox,
)
from PyQt6.QtCore import Qt

from config import ConfigManager
from ui.styles import COLORS
from lora_sync import (
    CFG_S3_PROFILE, CFG_S3_REGION, CFG_S3_ENDPOINT, CFG_S3_BUCKET,
    CFG_S3_LORAS_PREFIX, CFG_LORA_CHECK, S3_DEFAULTS, import_s3_browser_config,
)


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(750)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── ComfyUI Server ────────────────────────────────────────────────
        server_group = QGroupBox("ComfyUI Server")
        server_layout = QVBoxLayout(server_group)

        mode_row = QHBoxLayout()
        self._local_radio = QRadioButton("Local")
        self._runpod_radio = QRadioButton("RunPod")
        self._mode_btn_group = QButtonGroup()
        self._mode_btn_group.addButton(self._local_radio)
        self._mode_btn_group.addButton(self._runpod_radio)
        if config.get("mode", "local") == "runpod":
            self._runpod_radio.setChecked(True)
        else:
            self._local_radio.setChecked(True)
        mode_row.addWidget(self._local_radio)
        mode_row.addWidget(self._runpod_radio)
        mode_row.addStretch()
        server_layout.addLayout(mode_row)

        self._local_url_edit, _ = self._text_row(
            server_layout, "Local URL:",
            config.get("comfyui_url", "http://127.0.0.1:8000"),
            "http://127.0.0.1:8000"
        )
        self._runpod_edit, _ = self._text_row(
            server_layout, "RunPod URL:",
            config.get("runpod_url", ""),
            "https://xxxxxx-8188.proxy.runpod.net"
        )
        layout.addWidget(server_group)

        # ── Folders ───────────────────────────────────────────────────────
        folders_group = QGroupBox("Folders")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(10)

        self._workflow_edit, _ = self._folder_row(
            folders_layout, "Workflows:",
            config.get("workflow_dir", ""),
            "Folder containing workflow_segment_XX.json files..."
        )
        self._loras_edit, _ = self._folder_row(
            folders_layout, "LoRAs:",
            config.get("loras_dir", ""),
            "ComfyUI models/loras folder of the portable install you run (segment editor dropdown + LoRA check)..."
        )
        self._final_edit, _ = self._folder_row(
            folders_layout, "Final Video:",
            config.get("final_video_dir", ""),
            "Folder for the stitched final video..."
        )
        self._zip_edit, _ = self._folder_row(
            folders_layout, "Archive (.zip):",
            config.get("zip_output_dir", ""),
            "Folder for completed zip archives..."
        )
        layout.addWidget(folders_group)

        # ── Batch Processing ─────────────────────────────────────────────
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QVBoxLayout(batch_group)
        batch_layout.setSpacing(10)
        self._batch_local_edit, _ = self._folder_row(
            batch_layout, "Local Dir:",
            config.get("batch_dir_local", ""),
            "Local path where batch images are staged (e.g. B:/Batch_Processing)..."
        )
        self._batch_runpod_edit, _ = self._text_row(
            batch_layout, "RunPod Dir:",
            config.get("batch_dir_runpod", "/workspace/runpod-slim/Batch_Processing"),
            "RunPod path to the same folder (e.g. /workspace/runpod-slim/Batch_Processing)..."
        )
        self._runpod_input_edit, _ = self._text_row(
            batch_layout, "RunPod Input:",
            config.get("runpod_input_dir", "/workspace/runpod-slim/ComfyUI/input"),
            "Absolute path to ComfyUI's input folder on RunPod..."
        )
        layout.addWidget(batch_group)

        # ── RunPod Volume (S3) — LoRA check / sync ───────────────────────
        s3_group = QGroupBox("RunPod Volume (S3) — LoRA check && sync")
        s3_layout = QVBoxLayout(s3_group)
        s3_layout.setSpacing(10)
        self._lora_check_chk = QCheckBox(
            "Check that every LoRA a chain uses exists locally (and on the pod in RunPod mode) before a batch can start")
        self._lora_check_chk.setChecked(bool(config.get(CFG_LORA_CHECK, S3_DEFAULTS[CFG_LORA_CHECK])))
        s3_layout.addWidget(self._lora_check_chk)
        self._s3_profile_edit, _ = self._text_row(
            s3_layout, "AWS Profile:",
            config.get(CFG_S3_PROFILE, S3_DEFAULTS[CFG_S3_PROFILE]),
            "Profile name in %USERPROFILE%\\.aws\\credentials holding the RunPod S3 keys (e.g. runpod-s3)..."
        )
        self._s3_endpoint_edit, _ = self._text_row(
            s3_layout, "Endpoint URL:",
            config.get(CFG_S3_ENDPOINT, ""),
            "https://s3api-<datacenter>.runpod.io"
        )
        self._s3_region_edit, _ = self._text_row(
            s3_layout, "Region:",
            config.get(CFG_S3_REGION, ""),
            "RunPod datacenter id (e.g. us-ks-2)"
        )
        self._s3_bucket_edit, _ = self._text_row(
            s3_layout, "Bucket:",
            config.get(CFG_S3_BUCKET, ""),
            "Network volume id (e.g. pjez3nxwp9)"
        )
        self._s3_prefix_edit, _ = self._text_row(
            s3_layout, "LoRA Prefix:",
            config.get(CFG_S3_LORAS_PREFIX, S3_DEFAULTS[CFG_S3_LORAS_PREFIX]),
            "Path of ComfyUI's models/loras folder inside the bucket (e.g. runpod-slim/ComfyUI/models/loras/)"
        )
        s3_btn_row = QHBoxLayout()
        s3_btn_row.addStretch()
        import_btn = QPushButton("Import from S3 Browser config...")
        import_btn.setToolTip("Copy profile / endpoint / region / bucket from the S3 Browser app's config.json")
        import_btn.clicked.connect(self._import_s3_browser)
        test_btn = QPushButton("Test connection")
        test_btn.clicked.connect(self._test_s3)
        s3_btn_row.addWidget(import_btn)
        s3_btn_row.addWidget(test_btn)
        s3_layout.addLayout(s3_btn_row)
        self._s3_status = QLabel("")
        self._s3_status.setWordWrap(True)
        self._s3_status.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:9pt;")
        s3_layout.addWidget(self._s3_status)
        layout.addWidget(s3_group)

        # ── FFmpeg ────────────────────────────────────────────────────────
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        self._ffmpeg_edit, _ = self._file_row(
            ffmpeg_layout, "FFmpeg Path:",
            config.get("ffmpeg_path", "ffmpeg"),
            "Path to ffmpeg.exe (or 'ffmpeg' if on PATH)..."
        )
        layout.addWidget(ffmpeg_group)

        # ── AI Prompt Writer ─────────────────────────────────────────────
        prompt_ai_group = QGroupBox("AI Prompt Writer")
        prompt_ai_layout = QVBoxLayout(prompt_ai_group)
        self._anthropic_key_edit, _ = self._text_row(
            prompt_ai_layout, "API Key:",
            config.get("anthropic_api_key", ""),
            "Anthropic API key (console.anthropic.com) — used by the Prompt Writer tab..."
        )
        self._anthropic_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(prompt_ai_group)

        # ── Completion Sound ──────────────────────────────────────────────
        sound_group = QGroupBox("Completion Sound")
        sound_layout = QVBoxLayout(sound_group)
        sound_layout.setSpacing(10)

        self._sound_enabled_chk = QCheckBox("Play a sound when the batch finishes")
        self._sound_enabled_chk.setChecked(bool(config.get("completion_sound_enabled", False)))
        self._sound_enabled_chk.setStyleSheet(f"color: {COLORS['fg_primary']};")
        sound_layout.addWidget(self._sound_enabled_chk)

        self._sound_file_edit, _ = self._audio_file_row(
            sound_layout, "Sound File:",
            config.get("completion_sound_path", ""),
            "Path to a .wav or .mp3 audio file..."
        )
        layout.addWidget(sound_group)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    # Row builders
    # ------------------------------------------------------------------ #

    def _text_row(self, parent_layout, label: str, value: str, placeholder: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {COLORS['fg_primary']};")
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        parent_layout.addLayout(row)
        return edit, None

    def _folder_row(self, parent_layout, label: str, value: str, placeholder: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {COLORS['fg_primary']};")
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("...")
        btn.setFixedWidth(40)
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self._browse_folder(edit))
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent_layout.addLayout(row)
        return edit, btn

    def _file_row(self, parent_layout, label: str, value: str, placeholder: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {COLORS['fg_primary']};")
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("...")
        btn.setFixedWidth(40)
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self._browse_file(edit))
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent_layout.addLayout(row)
        return edit, btn

    def _browse_folder(self, edit: QLineEdit):
        current = edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", current or str(Path.home()))
        if folder:
            edit.setText(folder)

    def _audio_file_row(self, parent_layout, label: str, value: str, placeholder: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setStyleSheet(f"color: {COLORS['fg_primary']};")
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("...")
        btn.setFixedWidth(40)
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self._browse_audio(edit))
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent_layout.addLayout(row)
        return edit, btn

    def _browse_file(self, edit: QLineEdit):
        current = edit.text().strip()
        path, _ = QFileDialog.getOpenFileName(
            self, "Select FFmpeg", current or str(Path.home()),
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            edit.setText(path)

    def _browse_audio(self, edit: QLineEdit):
        current = edit.text().strip()
        start_dir = str(Path(current).parent) if current else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", start_dir,
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.aac *.m4a *.wma);;All Files (*)"
        )
        if path:
            edit.setText(path)

    def _s3_config_from_fields(self) -> dict:
        return {
            CFG_S3_PROFILE: self._s3_profile_edit.text().strip(),
            CFG_S3_ENDPOINT: self._s3_endpoint_edit.text().strip(),
            CFG_S3_REGION: self._s3_region_edit.text().strip(),
            CFG_S3_BUCKET: self._s3_bucket_edit.text().strip(),
            CFG_S3_LORAS_PREFIX: self._s3_prefix_edit.text().strip() or S3_DEFAULTS[CFG_S3_LORAS_PREFIX],
        }

    def _import_s3_browser(self):
        start = Path(r"P:/Apps/VibeCoded/S3 Browser/config.json")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select the S3 Browser config.json",
            str(start if start.exists() else Path.home()),
            "JSON (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            values = import_s3_browser_config(path)
        except Exception as e:  # noqa: BLE001
            self._s3_status.setText(f"Could not read {path}: {e}")
            return
        self._s3_profile_edit.setText(values.get(CFG_S3_PROFILE, self._s3_profile_edit.text()))
        self._s3_endpoint_edit.setText(values.get(CFG_S3_ENDPOINT, self._s3_endpoint_edit.text()))
        self._s3_region_edit.setText(values.get(CFG_S3_REGION, self._s3_region_edit.text()))
        self._s3_bucket_edit.setText(values.get(CFG_S3_BUCKET, self._s3_bucket_edit.text()))
        self._s3_status.setText(f"Imported {len(values)} value(s) from {Path(path).name}. Press Test connection to verify.")

    def _test_s3(self):
        from lora_sync import S3LoraStore
        self._s3_status.setText("Connecting...")
        self._s3_status.repaint()
        try:
            store = S3LoraStore(self._s3_config_from_fields())
            store.test_connection()
            count = len(store.list_remote())
            self._s3_status.setText(f"OK — {count} LoRA file(s) found under {store.prefix}")
        except Exception as e:  # noqa: BLE001
            self._s3_status.setText(f"Failed: {type(e).__name__}: {e}")

    def _save(self):
        self._config.set("mode", "local" if self._local_radio.isChecked() else "runpod")
        self._config.set(CFG_LORA_CHECK, self._lora_check_chk.isChecked())
        for key, value in self._s3_config_from_fields().items():
            self._config.set(key, value)
        self._config.set("comfyui_url", self._local_url_edit.text().strip())
        self._config.set("runpod_url", self._runpod_edit.text().strip())
        self._config.set("workflow_dir", self._workflow_edit.text().strip())
        self._config.set("loras_dir", self._loras_edit.text().strip())
        self._config.set("final_video_dir", self._final_edit.text().strip())
        self._config.set("zip_output_dir", self._zip_edit.text().strip())
        self._config.set("batch_dir_local", self._batch_local_edit.text().strip())
        self._config.set("batch_dir_runpod", self._batch_runpod_edit.text().strip())
        self._config.set("runpod_input_dir", self._runpod_input_edit.text().strip())
        self._config.set("ffmpeg_path", self._ffmpeg_edit.text().strip())
        self._config.set("completion_sound_enabled", self._sound_enabled_chk.isChecked())
        self._config.set("completion_sound_path", self._sound_file_edit.text().strip())
        self._config.set("anthropic_api_key", self._anthropic_key_edit.text().strip())
        self._config.save()
        self.accept()
