"""Prompt history (with the settings each prompt ran under) and the big
pop-out prompt editor.

History lives in ``<workflow>.prompt_history.json`` next to the workflow —
the same sidecar file the Chain Automator writes, so entries from either
app show up in both. Entries written here carry extra keys (``prompts``,
``settings``, ``source``, ``results``, ``favorite``, ``hidden``) that the
Automator simply ignores.

Nothing is ever dropped from the file: ``hidden`` only takes an entry out of
the default list, and the Hidden tab brings it back. The history is meant to
be a complete record, so curation is a view, not a deletion.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTabBar, QTextEdit,
    QVBoxLayout, QWidget,
)

from ui.styles import COLORS
from ui.widgets import NoScrollComboBox

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


def entry_matches(a: dict, b: dict) -> bool:
    """Whether two dicts are the same history entry.

    Entries carry no id, so identity is (timestamp, positive prompt, settings)
    — the triple Delete has always used. ``append_entry`` refuses to record a
    run that repeats the previous one with the same prompt and settings, so a
    false match needs two genuinely different runs logged in the same second
    with identical text and settings.
    """
    return (a.get("timestamp") == b.get("timestamp")
            and a.get("positive") == b.get("positive")
            and a.get("settings") == b.get("settings"))


def is_favorite(entry: dict) -> bool:
    return bool(entry.get("favorite"))


def is_hidden(entry: dict) -> bool:
    return bool(entry.get("hidden"))


def set_entry_flag(workflow_path: Path, entry: dict, key: str, value: bool) -> bool:
    """Persist ``favorite`` or ``hidden`` on one entry. Returns whether it landed.

    Re-reads the file rather than writing back the whole in-memory list, so a
    run recorded by the app (or the Chain Automator) while the dialog sat open
    is not clobbered by a tick-box.
    """
    entries = load_history(workflow_path)
    hit = False
    for e in entries:
        if entry_matches(e, entry):
            e[key] = bool(value)
            hit = True
    if hit:
        save_history(workflow_path, entries)
        entry[key] = bool(value)      # keep the row the dialog holds in step
    return hit


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
    """Search, filter, curate, inspect and reuse history entries — for the
    current template or across every template's history.

    The file keeps everything ever run. These tabs decide what you look at:
    star the prompts worth coming back to, untick the ones you never want to
    see again, and nothing is deleted either way.
    """
    use_prompt = pyqtSignal(dict)        # entry — prompt text only
    use_all = pyqtSignal(dict)           # entry — prompt + settings

    ALL_WORKFLOWS = "__all__"
    DATE_MODES = [("all", "All dates"), ("year", "Year"), ("month", "Month"), ("day", "Day")]

    # Views. "All" means all VISIBLE — Hidden is the way back to the rest.
    FAVORITES, RECENT, ALL, HIDDEN = range(4)
    VIEWS = [(FAVORITES, "★ Favorites"), (RECENT, "Recent"), (ALL, "All"), (HIDDEN, "Hidden")]
    RECENT_LIMIT = 100

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

        self._tabs = QTabBar()
        self._tabs.setExpanding(False)
        self._tabs.setToolTip(
            "Favorites — the prompts you starred\n"
            "Recent — the newest entries you haven't hidden\n"
            "All — everything you haven't hidden\n"
            "Hidden — tucked away, still in the file, untick to bring back")
        for _key, label in self.VIEWS:
            self._tabs.addTab(label)
        self._tabs.currentChanged.connect(lambda _i: self._populate())
        root.addWidget(self._tabs)

        wrow = QHBoxLayout()
        wrow.addWidget(QLabel("Template:"))
        self._wf_combo = NoScrollComboBox()
        self._wf_combo.setToolTip("The workflow JSON each history file belongs to")
        counts: dict[str, int] = {}
        for rel, _p, _e in self._rows:
            counts[rel] = counts.get(rel, 0) + 1
        self._wf_combo.addItem(f"All templates ({len(self._rows)})", self.ALL_WORKFLOWS)
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
        self._date_mode = NoScrollComboBox()
        for key, label in self.DATE_MODES:
            self._date_mode.addItem(label, key)
        self._date_mode.setFixedWidth(110)
        self._date_mode.currentIndexChanged.connect(self._on_filter_source_changed)
        frow.addWidget(self._date_mode)
        self._date_value = NoScrollComboBox()
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
        self._list.itemChanged.connect(self._on_item_checked)
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
        brow.addSpacing(18)
        self._fav_btn = QPushButton("★ Favorite")
        self._fav_btn.setObjectName("secondary_btn")
        self._fav_btn.setToolTip("Star this prompt so it shows on the Favorites tab")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        brow.addWidget(self._fav_btn)
        self._hide_btn = QPushButton("Hide")
        self._hide_btn.setObjectName("secondary_btn")
        self._hide_btn.setToolTip("Take this entry out of the list. It stays in the history "
                                  "file and comes back from the Hidden tab — same as the tick box.")
        self._hide_btn.clicked.connect(self._toggle_hidden)
        brow.addWidget(self._hide_btn)
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("secondary_btn")
        del_btn.setToolTip("Remove the entry from the history file for good. "
                           "To just get it out of the way, use Hide.")
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

    # An H3 prompt opens with a long templated preamble — the reference clause
    # ("For the target video, at 0.00 seconds ... is fully referenced"), then
    # the shot-1 framing — that is word-for-word identical across every run off
    # the same template. A preview taken from the top therefore makes all 58
    # rows read the same, which is useless when the job is picking out the ones
    # worth starring. Two steps fix it: jump past the known section header, then
    # drop whatever prefix the rows on screen actually turn out to share.
    PREVIEW_SKIP = ("integrated_multimodal_description:", "[Shot 1]")
    PREVIEW_WIDTH = 90
    PREFIX_SCAN = 1500       # H3 preambles run long; no point looking past this
    PREFIX_MIN = 30          # below this it is a coincidence, not boilerplate
    PREFIX_SHARE = 0.5       # the boilerplate only has to be the majority

    @classmethod
    def _prompt_body(cls, e: dict) -> str:
        """The entry's prompt as one line, past any known section header."""
        text = (e.get("positive")
                or next(iter((e.get("prompts") or {}).values()), {}).get("text", "")
                or "")
        for marker in cls.PREVIEW_SKIP:
            at = text.find(marker)
            if at != -1:
                text = text[at + len(marker):]
                break
        return " ".join(text.split())

    @classmethod
    def _shared_prefix(cls, bodies: list[str]) -> str:
        """The boilerplate opener the rows on screen share, to the last whole word.

        Deliberately a MAJORITY rather than all of them: one entry written
        against a different template, or hand-edited, would otherwise drag the
        common prefix to nothing and put every row back to reading the same.
        Rows that do not start with it are simply left untrimmed.
        """
        if len(bodies) < 2:
            return ""
        openers = Counter(b[:cls.PREFIX_MIN] for b in bodies if len(b) >= cls.PREFIX_MIN)
        if not openers:
            return ""
        opener, n = openers.most_common(1)[0]
        if n < 2 or n < len(bodies) * cls.PREFIX_SHARE:
            return ""
        group = [b for b in bodies if b.startswith(opener)]
        limit = min(cls.PREFIX_SCAN, min(len(b) for b in group))
        first = group[0]
        i = 0
        while i < limit and all(b[i] == first[i] for b in group):
            i += 1
        # Never cut mid-word: back up to the last space in the shared run.
        space = first.rfind(" ", 0, i)
        if space > 0:
            i = space + 1
        return first[:i] if i >= cls.PREFIX_MIN else ""

    @classmethod
    def _clip(cls, body: str, prefix: str) -> str:
        text = body[len(prefix):] if prefix and body.startswith(prefix) else body
        text = text.lstrip(" ,.;:-—")
        return text[:cls.PREVIEW_WIDTH] + ("…" if len(text) > cls.PREVIEW_WIDTH else "")

    @staticmethod
    def _entry_text(rel: str, e: dict) -> str:
        parts = [rel, e.get("positive", ""), e.get("negative", ""), describe_settings(e.get("settings")),
                 " ".join(e.get("results", []) or []), e.get("source", "") or ""]
        for p in (e.get("prompts") or {}).values():
            parts.append(p.get("text", ""))
        return "\n".join(parts).lower()

    def _view_rows(self, rows: list) -> list:
        """Apply the selected tab to an already workflow/date/search-filtered list."""
        view = self._tabs.currentIndex()
        if view == self.HIDDEN:
            return [r for r in rows if is_hidden(r[2])]
        visible = [r for r in rows if not is_hidden(r[2])]
        if view == self.FAVORITES:
            return [r for r in visible if is_favorite(r[2])]
        if view == self.RECENT:
            # Strictly newest first and capped: "recent" answers "what did I
            # just run", so floating favourites into it would defeat the tab.
            return visible[:self.RECENT_LIMIT]
        # All — the browse-everything view, so starred prompts lead.
        return sorted(visible, key=lambda r: not is_favorite(r[2]))

    def _update_tab_counts(self, rows: list):
        counts = {
            self.FAVORITES: sum(1 for r in rows if is_favorite(r[2]) and not is_hidden(r[2])),
            self.RECENT: min(self.RECENT_LIMIT, sum(1 for r in rows if not is_hidden(r[2]))),
            self.ALL: sum(1 for r in rows if not is_hidden(r[2])),
            self.HIDDEN: sum(1 for r in rows if is_hidden(r[2])),
        }
        for key, label in self.VIEWS:
            self._tabs.setTabText(key, f"{label} ({counts[key]})")

    def _populate(self):
        q = self._search.text().strip().lower()
        mode = self._date_mode.currentData()
        dval = self._date_value.currentData() if mode != "all" else ""
        show_wf = self._wf_combo.currentData() == self.ALL_WORKFLOWS
        rows = self._workflow_rows()
        matched = [
            r for r in rows
            if (not dval or self._date_key(r[2], mode) == dval)
            and (not q or q in self._entry_text(r[0], r[2]))
        ]
        self._update_tab_counts(matched)
        self._filtered = self._view_rows(matched)

        keep = self._selected
        bodies = [self._prompt_body(e) for _r, _p, e in self._filtered]
        prefix = self._shared_prefix(bodies)
        # Tick boxes are written here, and each write fires itemChanged.
        self._list.blockSignals(True)
        self._list.clear()
        for (rel, _p, e), body in zip(self._filtered, bodies):
            preview = self._clip(body, prefix)
            line = ("★ " if is_favorite(e) else "") + e.get("timestamp", "?")
            if show_wf:
                line += f"   [{rel}]"
            settings = describe_settings(e.get("settings"))
            if settings:
                line += f"   {settings}"
            if e.get("results"):
                line += f"   → {Path(e['results'][-1]).name}"
            item = QListWidgetItem(line + "\n    " + preview)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Ticked = shown in the list. Unticking hides without deleting.
            item.setCheckState(Qt.CheckState.Unchecked if is_hidden(e) else Qt.CheckState.Checked)
            self._list.addItem(item)
        self._list.blockSignals(False)

        self._count_lbl.setText(f"{len(self._filtered)} of {len(rows)}")
        row = next((n for n, r in enumerate(self._filtered)
                    if keep is not None and r[1] == keep[1] and entry_matches(r[2], keep[2])), 0)
        if self._filtered:
            self._list.setCurrentRow(row)
            self._on_select(row)
        else:
            self._selected = None
            self._preview.setPlainText("")
        for b in (self._use_btn, self._use_all_btn, self._fav_btn, self._hide_btn):
            b.setEnabled(bool(self._filtered))

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._filtered):
            self._selected = None
            self._preview.setPlainText("")
            return
        self._selected = self._filtered[row]
        rel, _p, e = self._selected
        head = f"Workflow: {rel}\n" if rel != self._current_rel else ""
        self._preview.setPlainText(head + format_entry(e))
        self._fav_btn.setText("★ Unfavorite" if is_favorite(e) else "★ Favorite")
        self._hide_btn.setText("Unhide" if is_hidden(e) else "Hide")

    def _on_item_checked(self, item: QListWidgetItem):
        """Ticked means visible, so an untick sets hidden."""
        row = self._list.row(item)
        if not (0 <= row < len(self._filtered)):
            return
        _rel, wf_path, entry = self._filtered[row]
        self._set_flag(wf_path, entry, "hidden",
                       item.checkState() != Qt.CheckState.Checked)

    def _set_flag(self, wf_path: Path, entry: dict, key: str, value: bool):
        if not set_entry_flag(wf_path, entry, key, value):
            QMessageBox.warning(self, "Could not save",
                                f"That entry is no longer in {wf_path.name}'s history file.")
            self._load_rows()
        self._populate()

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _emit(self, signal):
        if self._selected is not None:
            signal.emit(self._selected[2])
            self.close()

    def _toggle_favorite(self):
        if self._selected is None:
            return
        _rel, wf_path, entry = self._selected
        self._set_flag(wf_path, entry, "favorite", not is_favorite(entry))

    def _toggle_hidden(self):
        if self._selected is None:
            return
        _rel, wf_path, entry = self._selected
        self._set_flag(wf_path, entry, "hidden", not is_hidden(entry))

    def _delete(self):
        if self._selected is None:
            return
        rel, wf_path, entry = self._selected
        if QMessageBox.question(
                self, "Delete entry",
                f"Delete this history entry from {rel} for good?\n\n"
                f"To keep the record but take it out of the list, untick it "
                f"(or press Hide) instead.") != QMessageBox.StandardButton.Yes:
            return
        entries = load_history(wf_path)
        entries = [x for x in entries if not (
            x.get("timestamp") == entry.get("timestamp") and x.get("positive") == entry.get("positive")
            and x.get("settings") == entry.get("settings"))]
        save_history(wf_path, entries)
        self._load_rows()
        self._rebuild_date_values()
        self._populate()
