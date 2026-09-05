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
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
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
    if settings.get("steps") is not None:
        bits.append(f"Steps {settings['steps']}")
    if settings.get("megapixels") is not None:
        bits.append(f"{settings['megapixels']:g} MP")
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


def format_entry(e: dict) -> str:
    """Multi-line human-readable dump of one history entry."""
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
        if s.get("steps") is not None:
            lines.append(f"Steps: {s['steps']}")
        if s.get("megapixels") is not None:
            lines.append(f"Megapixels: {s['megapixels']:g}")
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
    return "\n".join(lines)


_LOOKUP_CACHE: dict[str, tuple[float, list[dict]]] = {}


def find_entry_for_result(workflow_dir: Path, filename: str) -> tuple[Path, dict] | None:
    """Scan every history file under the workflow folder for the entry whose
    results list names this file. Returns (workflow json path, entry)."""
    if not workflow_dir or not workflow_dir.is_dir():
        return None
    for hist in workflow_dir.rglob(f"*{HISTORY_SUFFIX}"):
        try:
            mtime = hist.stat().st_mtime
        except OSError:
            continue
        key = str(hist)
        cached = _LOOKUP_CACHE.get(key)
        if cached is None or cached[0] != mtime:
            try:
                with open(hist, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = []
            entries = data if isinstance(data, list) else []
            _LOOKUP_CACHE[key] = (mtime, entries)
        else:
            entries = cached[1]
        for entry in reversed(entries):
            if filename in (entry.get("results") or []):
                wf_path = hist.with_name(hist.name[: -len(HISTORY_SUFFIX)] + ".json")
                return wf_path, entry
    return None


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
    """Search, filter (workflow / date), inspect, reuse and delete history
    entries — for the current workflow or across every workflow's history."""
    use_prompt = pyqtSignal(dict)        # entry — prompt text only
    use_all = pyqtSignal(dict)           # entry — prompt + settings

    ALL_WORKFLOWS = "__all__"
    DATE_MODES = [("all", "All dates"), ("year", "Year"), ("month", "Month"), ("day", "Day")]

    def __init__(self, workflow_path: Path, parent=None, workflow_dir: Path | None = None):
        super().__init__(parent)
        self._workflow_path = workflow_path
        self._workflow_dir = workflow_dir
        self._current_rel = self._rel(workflow_path)
        # (rel, workflow json path, entry) for every entry, newest first
        self._rows: list[tuple[str, Path, dict]] = []
        self._filtered: list[tuple[str, Path, dict]] = []
        self._selected: tuple[str, Path, dict] | None = None
        self._load_rows()

        self.setWindowTitle(f"Prompt History — {workflow_path.name}")
        self.setMinimumSize(1000, 620)
        self.resize(1360, 800)
        self.setStyleSheet(parent.window().styleSheet() if parent else "")
        self._build_ui()
        self._rebuild_date_values()
        self._populate()

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #

    def _rel(self, wf_path: Path) -> str:
        if self._workflow_dir is not None:
            try:
                return wf_path.relative_to(self._workflow_dir).as_posix()
            except ValueError:
                pass
        return wf_path.name

    def _load_rows(self):
        self._rows = []
        files: list[Path] = []
        if self._workflow_dir is not None and self._workflow_dir.is_dir():
            files = sorted(self._workflow_dir.rglob(f"*{HISTORY_SUFFIX}"), key=lambda p: str(p).lower())
        own = history_path(self._workflow_path)
        if own not in files:
            files.insert(0, own)
        for hist in files:
            wf_path = hist.with_name(hist.name[: -len(HISTORY_SUFFIX)] + ".json")
            rel = self._rel(wf_path)
            try:
                with open(hist, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, list):
                for e in data:
                    if isinstance(e, dict):
                        self._rows.append((rel, wf_path, e))
        self._rows.sort(key=lambda r: r[2].get("timestamp", ""), reverse=True)

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        wrow = QHBoxLayout()
        wrow.addWidget(QLabel("Workflow:"))
        self._wf_combo = QComboBox()
        counts: dict[str, int] = {}
        for rel, _p, _e in self._rows:
            counts[rel] = counts.get(rel, 0) + 1
        self._wf_combo.addItem(f"All workflows ({len(self._rows)})", self.ALL_WORKFLOWS)
        self._wf_combo.addItem(f"{self._current_rel} ({counts.get(self._current_rel, 0)})  — current", self._current_rel)
        for rel in sorted(counts, key=str.lower):
            if rel != self._current_rel:
                self._wf_combo.addItem(f"{rel} ({counts[rel]})", rel)
        self._wf_combo.setCurrentIndex(1)
        self._wf_combo.currentIndexChanged.connect(self._on_filter_source_changed)
        wrow.addWidget(self._wf_combo, stretch=1)
        root.addLayout(wrow)

        frow = QHBoxLayout()
        frow.addWidget(QLabel("Date:"))
        self._date_mode = QComboBox()
        for key, label in self.DATE_MODES:
            self._date_mode.addItem(label, key)
        self._date_mode.setFixedWidth(110)
        self._date_mode.currentIndexChanged.connect(self._on_filter_source_changed)
        frow.addWidget(self._date_mode)
        self._date_value = QComboBox()
        self._date_value.setMinimumWidth(190)
        self._date_value.currentIndexChanged.connect(lambda _i: self._populate())
        frow.addWidget(self._date_value)
        frow.addSpacing(14)
        frow.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by prompt text, LoRA name, seed, steps, result file, source image…")
        self._search.textChanged.connect(self._populate)
        frow.addWidget(self._search, stretch=1)
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("status_dim")
        frow.addWidget(self._count_lbl)
        root.addLayout(frow)

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
        split.setSizes([560, 800])
        root.addWidget(split, stretch=1)

        brow = QHBoxLayout()
        self._use_btn = QPushButton("Use prompt")
        self._use_btn.setToolTip("Load only the prompt text into the editor")
        self._use_btn.clicked.connect(lambda: self._emit(self.use_prompt))
        brow.addWidget(self._use_btn)
        self._use_all_btn = QPushButton("Use prompt + settings")
        self._use_all_btn.setToolTip("Load the prompt and restore the LoRAs, strengths, seed, steps, megapixels and length it ran with")
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
    # Filtering
    # ------------------------------------------------------------------ #

    def _workflow_rows(self) -> list[tuple[str, Path, dict]]:
        sel = self._wf_combo.currentData()
        if sel == self.ALL_WORKFLOWS:
            return self._rows
        return [r for r in self._rows if r[0] == sel]

    @staticmethod
    def _date_key(entry: dict, mode: str) -> str:
        ts = entry.get("timestamp", "") or ""
        return {"year": ts[:4], "month": ts[:7], "day": ts[:10]}.get(mode, "")

    def _on_filter_source_changed(self, *_):
        self._rebuild_date_values()
        self._populate()

    def _rebuild_date_values(self):
        mode = self._date_mode.currentData()
        prev = self._date_value.currentData()
        self._date_value.blockSignals(True)
        self._date_value.clear()
        if mode == "all":
            self._date_value.setEnabled(False)
            self._date_value.addItem("—", "")
        else:
            self._date_value.setEnabled(True)
            counts: dict[str, int] = {}
            for _r, _p, e in self._workflow_rows():
                k = self._date_key(e, mode)
                if k:
                    counts[k] = counts.get(k, 0) + 1
            for k in sorted(counts, reverse=True):
                self._date_value.addItem(f"{k}  ({counts[k]})", k)
            idx = self._date_value.findData(prev) if prev else -1
            self._date_value.setCurrentIndex(idx if idx >= 0 else 0)
        self._date_value.blockSignals(False)

    @staticmethod
    def _entry_text(rel: str, e: dict) -> str:
        parts = [rel, e.get("positive", ""), e.get("negative", ""), describe_settings(e.get("settings")),
                 " ".join(e.get("results", []) or []), e.get("source", "") or ""]
        for p in (e.get("prompts") or {}).values():
            parts.append(p.get("text", ""))
        return "\n".join(parts).lower()

    def _populate(self):
        q = self._search.text().strip().lower()
        mode = self._date_mode.currentData()
        dval = self._date_value.currentData() if mode != "all" else ""
        show_wf = self._wf_combo.currentData() == self.ALL_WORKFLOWS
        rows = self._workflow_rows()
        self._filtered = [
            r for r in rows
            if (not dval or self._date_key(r[2], mode) == dval)
            and (not q or q in self._entry_text(r[0], r[2]))
        ]
        self._list.clear()
        for rel, _p, e in self._filtered:
            preview = (e.get("positive") or next(iter((e.get("prompts") or {}).values()), {}).get("text", "") or "").replace("\n", " ")
            preview = preview[:90] + ("…" if len(preview) > 90 else "")
            line = e.get("timestamp", "?")
            if show_wf:
                line += f"   [{rel}]"
            settings = describe_settings(e.get("settings"))
            if settings:
                line += f"   {settings}"
            if e.get("results"):
                line += f"   → {Path(e['results'][-1]).name}"
            self._list.addItem(QListWidgetItem(line + "\n    " + preview))
        self._count_lbl.setText(f"{len(self._filtered)} of {len(rows)}")
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
        self._selected = self._filtered[row]
        rel, _p, e = self._selected
        head = f"Workflow: {rel}\n" if rel != self._current_rel else ""
        self._preview.setPlainText(head + format_entry(e))

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _emit(self, signal):
        if self._selected is not None:
            signal.emit(self._selected[2])
            self.close()

    def _delete(self):
        if self._selected is None:
            return
        rel, wf_path, entry = self._selected
        if QMessageBox.question(self, "Delete entry", f"Delete this history entry from {rel}?") != QMessageBox.StandardButton.Yes:
            return
        entries = load_history(wf_path)
        entries = [x for x in entries if not (
            x.get("timestamp") == entry.get("timestamp") and x.get("positive") == entry.get("positive")
            and x.get("settings") == entry.get("settings"))]
        save_history(wf_path, entries)
        self._load_rows()
        self._rebuild_date_values()
        self._populate()
