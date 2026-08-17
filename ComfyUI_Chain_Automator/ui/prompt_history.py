import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QTextEdit, QMessageBox,
)

from ui.styles import COLORS

HISTORY_SUFFIX = ".prompt_history.json"


def history_path(workflow_path: Path) -> Path:
    """Sibling history file for a workflow JSON, e.g. IMG_x.json -> IMG_x.prompt_history.json"""
    return workflow_path.parent / f"{workflow_path.stem}{HISTORY_SUFFIX}"


def load_history(workflow_path: Path) -> list[dict]:
    try:
        with open(history_path(workflow_path), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def append_history(workflow_path: Path, positive: str, negative: str) -> None:
    positive = positive.strip()
    negative = negative.strip()
    if not positive and not negative:
        return
    entries = load_history(workflow_path)
    if entries and entries[-1].get("positive") == positive and entries[-1].get("negative") == negative:
        return  # skip an exact repeat of the most recently saved entry
    entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positive": positive,
        "negative": negative,
    })
    _write_history(workflow_path, entries)


def _write_history(workflow_path: Path, entries: list[dict]) -> None:
    path = history_path(workflow_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except OSError:
        pass


class PromptHistoryDialog(QDialog):
    """Search, view, and reuse saved prompts for one workflow file."""

    def __init__(self, workflow_path: Path, parent=None):
        super().__init__(parent)
        self._workflow_path = workflow_path
        self._entries = list(reversed(load_history(workflow_path)))  # newest first
        self._filtered: list[dict] = []
        self._selected: dict | None = None

        self.setWindowTitle(f"Prompt History — {workflow_path.name}")
        self.setMinimumSize(760, 480)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        search_row = QHBoxLayout()
        search_lbl = QLabel("Search:")
        search_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']};")
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter by prompt text...")
        self._search_edit.textChanged.connect(self._populate_list)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self._search_edit, stretch=1)
        root.addLayout(search_row)

        body_row = QHBoxLayout()
        body_row.setSpacing(10)

        self._list = QListWidget()
        self._list.setMinimumWidth(300)
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.itemDoubleClicked.connect(lambda _: self._on_use())
        body_row.addWidget(self._list, stretch=1)

        preview_col = QVBoxLayout()
        pos_lbl = QLabel("Positive")
        pos_lbl.setStyleSheet(f"color:{COLORS['success']}; font-weight:bold; font-size:9pt;")
        self._pos_preview = QTextEdit()
        self._pos_preview.setReadOnly(True)
        neg_lbl = QLabel("Negative")
        neg_lbl.setStyleSheet(f"color:{COLORS['error']}; font-weight:bold; font-size:9pt;")
        self._neg_preview = QTextEdit()
        self._neg_preview.setReadOnly(True)
        self._neg_preview.setFixedHeight(90)
        preview_col.addWidget(pos_lbl)
        preview_col.addWidget(self._pos_preview)
        preview_col.addWidget(neg_lbl)
        preview_col.addWidget(self._neg_preview)
        body_row.addLayout(preview_col, stretch=2)

        root.addLayout(body_row, stretch=1)

        btn_row = QHBoxLayout()
        self._delete_btn = QPushButton("🗑  Delete")
        self._delete_btn.setObjectName("cancel_btn")
        self._delete_btn.clicked.connect(self._on_delete)
        self._use_btn = QPushButton("➜  Use")
        self._use_btn.clicked.connect(self._on_use)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._use_btn)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _populate_list(self):
        query = self._search_edit.text().strip().lower()
        self._list.clear()
        self._filtered = [
            e for e in self._entries
            if not query or query in e.get("positive", "").lower() or query in e.get("negative", "").lower()
        ]
        for e in self._filtered:
            preview = (e.get("positive") or e.get("negative") or "").replace("\n", " ").strip()
            if len(preview) > 70:
                preview = preview[:70] + "…"
            self._list.addItem(QListWidgetItem(f"{e.get('timestamp', '')}  —  {preview}"))
        self._update_buttons()

    def _on_row_changed(self, row: int):
        if 0 <= row < len(self._filtered):
            e = self._filtered[row]
            self._pos_preview.setPlainText(e.get("positive", ""))
            self._neg_preview.setPlainText(e.get("negative", ""))
        else:
            self._pos_preview.clear()
            self._neg_preview.clear()
        self._update_buttons()

    def _update_buttons(self):
        has_sel = self._list.currentRow() >= 0
        self._use_btn.setEnabled(has_sel)
        self._delete_btn.setEnabled(has_sel)

    def _on_use(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _on_delete(self):
        row = self._list.currentRow()
        if not (0 <= row < len(self._filtered)):
            return
        reply = QMessageBox.question(
            self, "Delete Entry", "Remove this prompt from history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._entries.remove(self._filtered[row])
        _write_history(self._workflow_path, list(reversed(self._entries)))
        self._populate_list()

    def selected_entry(self) -> dict | None:
        return self._selected
