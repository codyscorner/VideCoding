from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton,
)
from PyQt6.QtCore import Qt

from worker import PROMPT_SEPARATOR, parse_prompts
from ui.styles import COLORS


class PromptEditorDialog(QDialog):
    def __init__(self, prompts_file: Path, parent=None):
        super().__init__(parent)
        self._file = prompts_file
        self.setWindowTitle(f"Edit Prompts — {prompts_file.name}")
        self.setMinimumSize(700, 560)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QLabel(
            f'Separate prompts with:  <b>{PROMPT_SEPARATOR}</b>  on its own line.  '
            f'Each prompt can span multiple lines.  '
            f'Add a weight to bias random selection: <b>---- PROMPT START x3 -----</b> '
            f'(3x more likely to be picked than a weight-1 prompt).'
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._editor = QPlainTextEdit()
        self._editor.setTabChangesFocus(False)
        layout.addWidget(self._editor, stretch=1)

        self._editor.textChanged.connect(self._update_count)

        bottom = QHBoxLayout()
        self._count_lbl = QLabel("0 prompts")
        self._count_lbl.setObjectName("subtitle")
        bottom.addWidget(self._count_lbl)
        bottom.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(90)
        save_btn.clicked.connect(self._save)

        bottom.addWidget(cancel_btn)
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

    def _load(self):
        try:
            text = self._file.read_text(encoding="utf-8")
        except OSError:
            text = f"{PROMPT_SEPARATOR}\n"
        self._editor.setPlainText(text)

    def _update_count(self):
        n = len(parse_prompts(self._editor.toPlainText()))
        self._count_lbl.setText(f"{n} prompt{'s' if n != 1 else ''} detected")

    def _save(self):
        try:
            self._file.write_text(self._editor.toPlainText(), encoding="utf-8")
            self.accept()
        except OSError as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", str(exc))
