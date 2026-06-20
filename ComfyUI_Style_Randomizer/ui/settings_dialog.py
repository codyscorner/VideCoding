from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QDialogButtonBox, QCheckBox,
)
from PyQt6.QtCore import Qt

from config import ConfigManager
from ui.styles import COLORS


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(680)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── ComfyUI Server ────────────────────────────────────────────────
        server_group = QGroupBox("ComfyUI Server")
        server_layout = QVBoxLayout(server_group)
        server_layout.setSpacing(8)

        mode_row = QHBoxLayout()
        self._local_radio  = QRadioButton("Local")
        self._runpod_radio = QRadioButton("RunPod")
        self._mode_btn_group = QButtonGroup()
        self._mode_btn_group.addButton(self._local_radio)
        self._mode_btn_group.addButton(self._runpod_radio)
        (self._runpod_radio if config.get("mode", "local") == "runpod"
         else self._local_radio).setChecked(True)
        mode_row.addWidget(self._local_radio)
        mode_row.addWidget(self._runpod_radio)
        mode_row.addStretch()
        server_layout.addLayout(mode_row)

        self._local_url_edit = self._text_row(
            server_layout, "Local URL:",
            config.get("comfyui_url", "http://127.0.0.1:8000"),
            "http://127.0.0.1:8000",
        )
        self._runpod_edit = self._text_row(
            server_layout, "RunPod URL:",
            config.get("runpod_url", ""),
            "https://YOUR-POD-ID-8000.proxy.runpod.net/",
        )
        layout.addWidget(server_group)

        # ── Paths ─────────────────────────────────────────────────────────
        paths_group = QGroupBox("Paths")
        paths_layout = QVBoxLayout(paths_group)
        paths_layout.setSpacing(8)

        self._output_edit = self._folder_row(
            paths_layout, "Output Folder:",
            config.get("output_dir", ""),
            "Folder where styled images are saved…",
        )
        self._wf_edit = self._file_row(
            paths_layout, "Workflow JSON:",
            config.get("workflow_path", ""),
            "ComfyUI i2i workflow exported as API JSON…",
            file_filter="JSON Files (*.json)",
        )
        self._pr_edit, self._edit_prompts_btn = self._file_row_with_extra(
            paths_layout, "Prompts File:",
            config.get("prompts_file", ""),
            "Text file containing style prompts…",
            file_filter="Text Files (*.txt)",
            extra_label="Edit",
        )
        self._edit_prompts_btn.clicked.connect(self._open_prompt_editor)
        layout.addWidget(paths_group)

        # ── Options ───────────────────────────────────────────────────────
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self._skip_cb = QCheckBox(
            "Skip already-processed images  (checks output folder by filename stem)"
        )
        self._skip_cb.setChecked(config.get("skip_existing", True))
        options_layout.addWidget(self._skip_cb)
        layout.addWidget(options_group)

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

    def _text_row(self, parent_layout, label: str, value: str, placeholder: str) -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        parent_layout.addLayout(row)
        return edit

    def _folder_row(self, parent_layout, label: str, value: str, placeholder: str) -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("…")
        btn.setFixedWidth(36)
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self._browse_folder(edit))
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent_layout.addLayout(row)
        return edit

    def _file_row(self, parent_layout, label: str, value: str,
                  placeholder: str, file_filter: str = "") -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        btn = QPushButton("…")
        btn.setFixedWidth(36)
        btn.setFixedHeight(30)
        btn.clicked.connect(lambda: self._browse_file(edit, file_filter))
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(btn)
        parent_layout.addLayout(row)
        return edit

    def _file_row_with_extra(self, parent_layout, label: str, value: str,
                              placeholder: str, file_filter: str = "",
                              extra_label: str = "") -> tuple[QLineEdit, QPushButton]:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        edit = QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(36)
        browse_btn.setFixedHeight(30)
        browse_btn.clicked.connect(lambda: self._browse_file(edit, file_filter))
        extra_btn = QPushButton(extra_label)
        extra_btn.setFixedWidth(52)
        extra_btn.setFixedHeight(30)
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        row.addWidget(browse_btn)
        row.addWidget(extra_btn)
        parent_layout.addLayout(row)
        return edit, extra_btn

    # ------------------------------------------------------------------ #
    # Browse helpers
    # ------------------------------------------------------------------ #

    def _browse_folder(self, edit: QLineEdit):
        current = edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", current or str(Path.home()))
        if folder:
            edit.setText(folder)

    def _browse_file(self, edit: QLineEdit, file_filter: str = ""):
        current = edit.text().strip()
        start = str(Path(current).parent) if current else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Select File", start, file_filter or "All Files (*)")
        if path:
            edit.setText(path)

    def _open_prompt_editor(self):
        path = Path(self._pr_edit.text().strip())
        if not path.is_file():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No File", "Select a Prompts File first.")
            return
        from ui.prompt_editor import PromptEditorDialog
        dlg = PromptEditorDialog(path, self)
        dlg.exec()

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def _save(self):
        self._config.set("mode", "local" if self._local_radio.isChecked() else "runpod")
        self._config.set("comfyui_url",    self._local_url_edit.text().strip())
        self._config.set("runpod_url",     self._runpod_edit.text().strip())
        self._config.set("output_dir",     self._output_edit.text().strip())
        self._config.set("workflow_path",  self._wf_edit.text().strip())
        self._config.set("prompts_file",   self._pr_edit.text().strip())
        self._config.set("skip_existing",  self._skip_cb.isChecked())
        self._config.save()
        self.accept()
