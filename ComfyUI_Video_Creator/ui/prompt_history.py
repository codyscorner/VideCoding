"""Prompt history (with the settings each prompt ran under) and the big
pop-out prompt editor.

History lives in ``<workflow>.prompt_history.json`` next to the workflow —
the same sidecar file the Chain Automator writes, so entries from either
app show up in both. Entries written here carry extra keys (``prompts``,
``settings``, ``source``, ``results``) that the Automator simply ignores.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from ui.styles import COLORS

HISTORY_SUFFIX = ".prompt_history.json"
APP_TAG = "ComfyUI Video Creator"


# --------------------------------------------------------------------- #
# File access
# --------------------------------------------------------------------- #

def history_path(workflow_path: Path) -> Path:
    return workflow_path.parent / f"{workflow_path.stem}{HISTORY_SUFFIX}"


def load_history(workflow_path: Path) -> list[dict]:
    try:
        with open(history_path(workflow_path), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_history(workflow_path: Path, entries: list[dict]) -> None:
    path = history_path(workflow_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def make_entry(prompts: list[tuple[str, str, str, bool, str]], settings: dict, source: str) -> dict:
    """prompts: (node_id, key, label, negative, text) tuples."""
    positives = [t.strip() for _n, _k, _l, neg, t in prompts if not neg and t.strip()]
    negatives = [t.strip() for _n, _k, _l, neg, t in prompts if neg and t.strip()]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positive": "\n\n".join(positives),
        "negative": "\n\n".join(negatives),
        "prompts": {f"{nid}|{key}": {"label": label, "negative": neg, "text": text}
                    for nid, key, label, neg, text in prompts},
        "settings": settings,
        "source": source,
        "results": [],
        "app": APP_TAG,
    }


def _same_run(a: dict, b: dict) -> bool:
    return (a.get("positive") == b.get("positive") and a.get("negative") == b.get("negative")
            and a.get("settings") == b.get("settings"))


def append_entry(workflow_path: Path, entry: dict) -> int:
    """Append unless it exactly repeats the latest entry (same prompt AND
    same settings). Returns the index of the entry that now represents it."""
    entries = load_history(workflow_path)
    if entries and _same_run(entries[-1], entry):
        return len(entries) - 1
    entries.append(entry)
    save_history(workflow_path, entries)
    return len(entries) - 1


def add_results(workflow_path: Path, index: int, results: list[str]) -> None:
    entries = load_history(workflow_path)
    if 0 <= index < len(entries):
        existing = entries[index].setdefault("results", [])
        for r in results:
            if r not in existing:
                existing.append(r)
        save_history(workflow_path, entries)


def describe_settings(settings: dict | None) -> str:
    if not settings:
        return ""
    bits = []
    loras = [l for l in settings.get("loras", []) if l.get("name") and l.get("name") != "None"]
    if loras:
        bits.append("LoRAs: " + " · ".join(
            f"{Path(l['name']).stem} ({', '.join(f'{v:g}' for v in l.get('strengths', {}).values()) or '-'})"
            for l in loras))
    seed = settings.get("seed")
    bits.append(f"Seed {seed}" if seed is not None else "Seed random")
    length = settings.get("length")
    if length:
        val = length.get("value")
        bits.append(f"{length.get('label', 'Length')}: {val:g}" if isinstance(val, (int, float))
                    else f"{length.get('label', 'Length')}: {val}")
    if settings.get("video_input_mode"):
        bits.append(f"input {settings['video_input_mode']}")
    if settings.get("mode"):
        bits.append(settings["mode"])
    return "  |  ".join(bits)


# --------------------------------------------------------------------- #
# Dialogs
# --------------------------------------------------------------------- #

class PromptExpandDialog(QDialog):
    """Large pop-out editor for one prompt field."""

    def __init__(self, title: str, text: str, font: QFont, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit — {title}")
        self.setMinimumSize(900, 600)
        self.resize(1300, 820)
        self.setStyleSheet(parent.window().styleSheet() if parent else "")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {COLORS['accent_hover']}; font-weight: bold; font-size: 12pt;")
        layout.addWidget(lbl)
        self._edit = QTextEdit()
        self._edit.setAcceptRichText(False)
        self._edit.setPlainText(text)
        self._edit.setFont(QFont(font.family(), max(font.pointSize() + 1, 11)))
        layout.addWidget(self._edit, stretch=1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._edit.setFocus()

    def text(self) -> str:
        return self._edit.toPlainText()


class PromptHistoryDialog(QDialog):
    """Search, inspect, reuse and delete history entries for one workflow."""
    use_prompt = pyqtSignal(dict)        # entry — prompt text only
    use_all = pyqtSignal(dict)           # entry — prompt + settings

    def __init__(self, workflow_path: Path, parent=None):
        super().__init__(parent)
        self._workflow_path = workflow_path
        self._entries = list(reversed(load_history(workflow_path)))   # newest first
        self._filtered: list[dict] = []
        self._selected: dict | None = None

        self.setWindowTitle(f"Prompt History — {workflow_path.name}")
        self.setMinimumSize(1000, 600)
        self.resize(1300, 760)
        self.setStyleSheet(parent.window().styleSheet() if parent else "")
        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        srow = QHBoxLayout()
        srow.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by prompt text, LoRA name, seed, result file…")
        self._search.textChanged.connect(self._populate)
        srow.addWidget(self._search, stretch=1)
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("status_dim")
        srow.addWidget(self._count_lbl)
        root.addLayout(srow)

        split = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setStyleSheet("QListWidget { font-family: 'Segoe UI'; font-size: 9.5pt; }")
        self._list.setWordWrap(True)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.currentRowChanged.connect(self._on_select)
        split.addWidget(self._list)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        rl.addWidget(self._preview, stretch=1)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setSizes([520, 780])
        root.addWidget(split, stretch=1)

        brow = QHBoxLayout()
        self._use_btn = QPushButton("Use prompt")
        self._use_btn.setToolTip("Load only the prompt text into the editor")
        self._use_btn.clicked.connect(lambda: self._emit(self.use_prompt))
        brow.addWidget(self._use_btn)
        self._use_all_btn = QPushButton("Use prompt + settings")
        self._use_all_btn.setToolTip("Load the prompt and restore the LoRAs, strengths, seed and length it ran with")
        self._use_all_btn.clicked.connect(lambda: self._emit(self.use_all))
        brow.addWidget(self._use_all_btn)
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("secondary_btn")
        del_btn.clicked.connect(self._delete)
        brow.addWidget(del_btn)
        brow.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary_btn")
        close_btn.clicked.connect(self.close)
        brow.addWidget(close_btn)
        root.addLayout(brow)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _entry_text(e: dict) -> str:
        parts = [e.get("positive", ""), e.get("negative", ""), describe_settings(e.get("settings")),
                 " ".join(e.get("results", []) or []), e.get("source", "") or ""]
        for p in (e.get("prompts") or {}).values():
            parts.append(p.get("text", ""))
        return "\n".join(parts).lower()

    def _populate(self):
        q = self._search.text().strip().lower()
        self._filtered = [e for e in self._entries if not q or q in self._entry_text(e)]
        self._list.clear()
        for e in self._filtered:
            preview = (e.get("positive") or next(iter((e.get("prompts") or {}).values()), {}).get("text", "") or "").replace("\n", " ")
            preview = preview[:90] + ("…" if len(preview) > 90 else "")
            settings = describe_settings(e.get("settings"))
            line = f"{e.get('timestamp', '?')}"
            if settings:
                line += f"   {settings}"
            if e.get("results"):
                line += f"   → {Path(e['results'][-1]).name}"
            item = QListWidgetItem(line + "\n    " + preview)
            self._list.addItem(item)
        self._count_lbl.setText(f"{len(self._filtered)} of {len(self._entries)}")
        if self._filtered:
            self._list.setCurrentRow(0)
        else:
            self._selected = None
            self._preview.setPlainText("")
        self._use_btn.setEnabled(bool(self._filtered))
        self._use_all_btn.setEnabled(bool(self._filtered))

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._filtered):
            self._selected = None
            self._preview.setPlainText("")
            return
        e = self._filtered[row]
        self._selected = e
        lines = [f"Saved: {e.get('timestamp', '?')}"]
        if e.get("source"):
            lines.append(f"Source: {e['source']}")
        if e.get("app"):
            lines.append(f"App: {e['app']}")
        lines.append("")
        prompts = e.get("prompts") or {}
        if prompts:
            for p in prompts.values():
                lines += [f"── {p.get('label', 'Prompt')} ──", p.get("text", ""), ""]
        else:
            lines += ["── Positive ──", e.get("positive", ""), ""]
            if e.get("negative"):
                lines += ["── Negative ──", e.get("negative", ""), ""]
        s = e.get("settings") or {}
        if s:
            lines.append("── Settings ──")
            lines.append(f"Workflow: {s.get('workflow', '?')}   Mode: {s.get('mode', '?')}")
            seed = s.get("seed")
            lines.append(f"Seed: {seed if seed is not None else 'random'}")
            if s.get("length"):
                val = s["length"].get("value")
                lines.append(f"{s['length'].get('label', 'Length')}: {val:g}" if isinstance(val, (int, float))
                             else f"{s['length'].get('label', 'Length')}: {val}")
            for l in s.get("loras", []):
                strengths = ", ".join(f"{k}={v:g}" for k, v in (l.get("strengths") or {}).items())
                lines.append(f"LoRA {l.get('label', '')}: {l.get('name', 'None')}  {strengths}")
            if s.get("video_input_mode"):
                lines.append(f"Video input: {s['video_input_mode']}   Append to source: {s.get('extend_stitch')}")
            lines.append("")
        if e.get("results"):
            lines.append("── Results ──")
            lines += e["results"]
        self._preview.setPlainText("\n".join(lines))

    def _emit(self, signal):
        if self._selected is not None:
            signal.emit(self._selected)
            self.close()

    def _delete(self):
        if self._selected is None:
            return
        if QMessageBox.question(self, "Delete entry", "Delete this history entry?") != QMessageBox.StandardButton.Yes:
            return
        entries = load_history(self._workflow_path)
        entries = [x for x in entries if x is not self._selected and not (
            x.get("timestamp") == self._selected.get("timestamp") and x.get("positive") == self._selected.get("positive"))]
        save_history(self._workflow_path, entries)
        self._entries = list(reversed(entries))
        self._populate()
