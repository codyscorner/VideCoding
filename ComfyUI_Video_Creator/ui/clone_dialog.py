"""Clone-a-workflow dialog: new name, destination subfolder, and whether the
clone starts from the file on disk or from the edits currently on screen."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QVBoxLayout,
)

from ui.styles import COLORS
from workflow_tools import (
    check_workflow_name, list_workflow_folders, unique_workflow_path, workflow_stem,
)

ROOT_LABEL = "(Workflows folder)"


class CloneWorkflowDialog(QDialog):
    """Ask for the clone's name and folder. `result_path()` is valid after accept()."""

    def __init__(self, workflow_dir: Path, source_rel: str, has_edits: bool, parent=None):
        super().__init__(parent)
        self._dir = workflow_dir
        self._path: Path | None = None
        self.setWindowTitle("Clone workflow")
        self.setMinimumWidth(560)
        self.setStyleSheet(parent.window().styleSheet() if parent else "")

        src = Path(source_rel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel(f"Copy of {src.name}")
        title.setStyleSheet(f"color: {COLORS['accent_hover']}; font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        blurb = QLabel("The original is left untouched — the copy is selected when you close this "
                       "dialog, so anything you change and save from here on lands in the copy.")
        blurb.setWordWrap(True)
        blurb.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(blurb)

        form = QFormLayout()
        form.setSpacing(6)

        self._name = QLineEdit()
        self._name.setPlaceholderText("New workflow name")
        self._name.textChanged.connect(self._validate)
        form.addRow("New name:", self._name)

        self._folder = QComboBox()
        folders = list_workflow_folders(workflow_dir)
        src_folder = src.parent.as_posix()
        if src_folder == ".":
            src_folder = ""
        if src_folder not in folders:
            folders.append(src_folder)
        for rel in folders:
            self._folder.addItem(ROOT_LABEL if rel == "" else rel, rel)
        idx = self._folder.findData(src_folder)
        self._folder.setCurrentIndex(max(idx, 0))
        self._folder.currentIndexChanged.connect(self._validate)
        form.addRow("Folder:", self._folder)
        layout.addLayout(form)

        self._with_edits = QCheckBox("Start from the prompts, LoRAs and settings shown in the panel")
        self._with_edits.setToolTip(
            "On: the prompts, LoRAs, steps, megapixels and length on screen are written into the clone.\n"
            "Off: the clone is a byte-for-byte copy of the saved file and the panel reloads from it, "
            "so unsaved edits on screen are discarded.")
        self._with_edits.setChecked(has_edits)
        self._with_edits.setEnabled(has_edits)
        layout.addWidget(self._with_edits)

        self._with_history = QCheckBox("Copy the prompt history too")
        self._with_history.setToolTip("The clone starts with its own copy of the original's run history.\n"
                                      "Off: the clone starts with an empty history (the original's is "
                                      "still readable from the History dialog).")
        layout.addWidget(self._with_history)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                         | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create clone")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        suggested = unique_workflow_path(workflow_dir / src_folder, f"{src.stem} copy").stem \
            if workflow_dir.is_dir() else f"{src.stem} copy"
        self._name.setText(suggested)
        self._name.setFocus()
        self._name.selectAll()

    # ------------------------------------------------------------------ #

    def _target(self) -> Path:
        folder = self._folder.currentData() or ""
        return self._dir / folder / f"{workflow_stem(self._name.text())}.json"

    def _validate(self):
        problem = check_workflow_name(self._name.text())
        if not problem and self._target().exists():
            problem = f"{self._target().name} already exists in that folder."
        ok = not problem
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
        if ok:
            rel = self._target().relative_to(self._dir).as_posix()
            self._status.setText(f"Creates {rel}")
            self._status.setStyleSheet(f"color: {COLORS['fg_dim']};")
        else:
            self._status.setText(problem)
            self._status.setStyleSheet(f"color: {COLORS['error']};")

    def accept(self):
        self._validate()
        if not self._buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            return
        self._path = self._target()
        super().accept()

    # ------------------------------------------------------------------ #

    def result_path(self) -> Path | None:
        return self._path

    def with_edits(self) -> bool:
        return self._with_edits.isChecked()

    def with_history(self) -> bool:
        return self._with_history.isChecked()
