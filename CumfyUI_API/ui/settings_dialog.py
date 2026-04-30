from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from config import ConfigManager
from ui.styles import COLORS


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

        self._runpod_edit, _ = self._text_row(
            server_layout, "RunPod URL:",
            config.get("runpod_url", ""),
            "https://xxxxxx-8188.proxy.runpod.net"
        )
        layout.addWidget(server_group)

        # ── Output Folders ────────────────────────────────────────────────
        folders_group = QGroupBox("Output Folders")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(10)

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

        # ── FFmpeg ────────────────────────────────────────────────────────
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        self._ffmpeg_edit, _ = self._file_row(
            ffmpeg_layout, "FFmpeg Path:",
            config.get("ffmpeg_path", "ffmpeg"),
            "Path to ffmpeg.exe (or 'ffmpeg' if on PATH)..."
        )
        layout.addWidget(ffmpeg_group)

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

    def _browse_file(self, edit: QLineEdit):
        current = edit.text().strip()
        path, _ = QFileDialog.getOpenFileName(
            self, "Select FFmpeg", current or str(Path.home()),
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            edit.setText(path)

    def _save(self):
        self._config.set("mode", "local" if self._local_radio.isChecked() else "runpod")
        self._config.set("runpod_url", self._runpod_edit.text().strip())
        self._config.set("final_video_dir", self._final_edit.text().strip())
        self._config.set("zip_output_dir", self._zip_edit.text().strip())
        self._config.set("ffmpeg_path", self._ffmpeg_edit.text().strip())
        self._config.save()
        self.accept()
