import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QTextEdit, QMessageBox,
)

from ui.styles import COLORS


def load_history(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def append_history(path: Path, entry: dict) -> None:
    idea = entry.get("idea", "").strip()
    output = entry.get("output", "").strip()
    if not idea and not output:
        return
    entries = load_history(path)
    if entries and entries[-1].get("idea") == idea and entries[-1].get("output") == output:
        return  # skip an exact repeat of the most recently saved entry
    entry = {**entry, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    entries.append(entry)
    _write_history(path, entries)


def _write_history(path: Path, entries: list[dict]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except OSError:
        pass


class HistoryDialog(QDialog):
    """Search, view, and reuse previously generated prompts."""

    def __init__(self, history_path: Path, parent=None):
        super().__init__(parent)
        self._history_path = history_path
        self._entries = list(reversed(load_history(history_path)))  # newest first
        self._filtered: list[dict] = []
        self._selected: dict | None = None

        self.setWindowTitle("Prompt History")
        self.setMinimumSize(820, 520)
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
        self._search_edit.setPlaceholderText("Filter by idea or output text...")
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
        idea_lbl = QLabel("Idea")
        idea_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-weight:bold; font-size:9pt;")
        self._idea_preview = QTextEdit()
        self._idea_preview.setReadOnly(True)
        self._idea_preview.setFixedHeight(80)
        out_lbl = QLabel("Generated Prompt")
        out_lbl.setStyleSheet(f"color:{COLORS['success']}; font-weight:bold; font-size:9pt;")
        self._output_preview = QTextEdit()
        self._output_preview.setReadOnly(True)
        preview_col.addWidget(idea_lbl)
        preview_col.addWidget(self._idea_preview)
        preview_col.addWidget(out_lbl)
        preview_col.addWidget(self._output_preview)
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
            if not query or query in e.get("idea", "").lower() or query in e.get("output", "").lower()
        ]
        for e in self._filtered:
            preview = (e.get("idea") or e.get("output") or "").replace("\n", " ").strip()
            if len(preview) > 60:
                preview = preview[:60] + "…"
            tag = f"{e.get('provider', '')}/{e.get('model', '')}".strip("/")
            self._list.addItem(QListWidgetItem(f"{e.get('timestamp', '')}  [{tag}]  {preview}"))
        self._update_buttons()

    def _on_row_changed(self, row: int):
        if 0 <= row < len(self._filtered):
            e = self._filtered[row]
            self._idea_preview.setPlainText(e.get("idea", ""))
            self._output_preview.setPlainText(e.get("output", ""))
        else:
            self._idea_preview.clear()
            self._output_preview.clear()
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
        _write_history(self._history_path, list(reversed(self._entries)))
        self._populate_list()

    def selected_entry(self) -> dict | None:
        return self._selected
