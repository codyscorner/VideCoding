from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt

from config import ConfigManager
from ui.styles import COLORS


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Mode group
        mode_group = QGroupBox("ComfyUI Mode")
        mode_v = QVBoxLayout(mode_group)

        self._local_radio  = QRadioButton("Local  (same machine)")
        self._runpod_radio = QRadioButton("RunPod  (remote proxy)")
        self._mode_group   = QButtonGroup(self)
        self._mode_group.addButton(self._local_radio,  0)
        self._mode_group.addButton(self._runpod_radio, 1)

        mode = self._config.get("mode", "local")
        (self._runpod_radio if mode == "runpod" else self._local_radio).setChecked(True)

        mode_v.addWidget(self._local_radio)
        mode_v.addWidget(self._runpod_radio)
        layout.addWidget(mode_group)

        # URLs
        url_group = QGroupBox("URLs")
        url_v = QVBoxLayout(url_group)

        self._local_url = self._make_field(
            url_v, "Local URL:", self._config.get("comfyui_url", "http://127.0.0.1:8000")
        )
        self._runpod_url = self._make_field(
            url_v, "RunPod URL:", self._config.get("runpod_url", "")
        )
        self._runpod_url.setPlaceholderText("https://YOUR-POD-ID-8000.proxy.runpod.net/")
        layout.addWidget(url_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(90)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _make_field(self, parent_layout, label: str, value: str) -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(90)
        edit = QLineEdit(value)
        row.addWidget(lbl)
        row.addWidget(edit)
        parent_layout.addLayout(row)
        return edit

    def _save(self):
        self._config.set("mode", "runpod" if self._runpod_radio.isChecked() else "local")
        self._config.set("comfyui_url", self._local_url.text().strip())
        self._config.set("runpod_url",  self._runpod_url.text().strip())
        self.accept()
