"""Library tab: browse finished videos (the Output folder by default),
play them, delete them, send one back to the Extend tab, and see the
prompt + settings that produced each one (from the prompt history)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from config import ConfigManager
from file_ops import archive_paths, delete_paths, thumbnail_caches
from media_tools import probe
from ui.prompt_history import find_entry_for_result, format_entry
from ui.styles import COLORS
from ui.widgets import MediaBrowser


def _fmt_size(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024:.0f} KB"


def _fmt_dur(seconds: float) -> str:
    s = int(round(seconds))
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}" if m else f"{seconds:.1f}s"


class LibraryTab(QWidget):
    play_requested = pyqtSignal(list)        # list[str] playlist
    send_to_extend = pyqtSignal(object)      # Path
    reuse_requested = pyqtSignal(object, object, object)  # result video Path, workflow Path, history entry dict
    folder_changed = pyqtSignal(str)

    DATE_MODES = [("all", "All dates"), ("year", "Year"), ("month", "Month"), ("day", "Day")]

    def __init__(self, config: ConfigManager, ffmpeg_getter, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._ffmpeg_getter = ffmpeg_getter
        self._detail_hit: tuple[Path, dict] | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        split = QSplitter(Qt.Orientation.Horizontal)

        self.browser = MediaBrowser(
            "video", self.effective_folder(), config.get("library_sort", "Newest First"),
            ffmpeg_getter, multi=True, last_frame=False, title="Library", show_delete=False,
            hint="Finished videos — Output folder unless you pick another one",
        )
        self.browser.selection_changed.connect(lambda _p: self._update_details())
        self.browser.activated.connect(lambda p: self.play_requested.emit([str(p)]))
        self.browser.folder_changed.connect(self._on_folder_changed)
        self.browser.sort_changed.connect(lambda s: (config.set("library_sort", s), config.save()))
        self.browser.loaded.connect(self._on_loaded)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        filt_row = QHBoxLayout()
        filt_row.setSpacing(6)
        filt_row.addWidget(QLabel("Search:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by filename…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        filt_row.addWidget(self._search, stretch=1)
        filt_row.addWidget(QLabel("Date:"))
        self._date_mode = QComboBox()
        for key, label in self.DATE_MODES:
            self._date_mode.addItem(label, key)
        self._date_mode.setFixedWidth(100)
        self._date_mode.currentIndexChanged.connect(self._on_date_mode_changed)
        filt_row.addWidget(self._date_mode)
        self._date_value = QComboBox()
        self._date_value.setMinimumWidth(160)
        self._date_value.setEnabled(False)
        self._date_value.addItem("—", "")
        self._date_value.currentIndexChanged.connect(lambda _i: self._apply_filter())
        filt_row.addWidget(self._date_value)
        self._filter_status = QLabel("")
        self._filter_status.setObjectName("status_dim")
        filt_row.addWidget(self._filter_status)
        left_lay.addLayout(filt_row)

        left_lay.addWidget(self.browser, stretch=1)
        split.addWidget(left)

        right = QWidget()
        right.setMinimumWidth(380)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        btn_group = QGroupBox("Actions")
        bl = QVBoxLayout(btn_group)
        bl.setSpacing(6)
        row1 = QHBoxLayout()
        play_btn = QPushButton("▶  Play")
        play_btn.setToolTip("Play the selected video(s) back-to-back")
        play_btn.clicked.connect(self._play_selected)
        row1.addWidget(play_btn)
        extend_btn = QPushButton("🎬  Send to Extend")
        extend_btn.setToolTip("Use this video as the source on the Video → Extend tab")
        extend_btn.clicked.connect(self._send_selected)
        row1.addWidget(extend_btn)
        self._reuse_btn = QPushButton("🔁 Reuse Settings")
        self._reuse_btn.setToolTip(
            "Reload this run's prompt, LoRAs, seed, steps and source image/video into the matching "
            "tab so you can tweak it and try again")
        self._reuse_btn.setEnabled(False)
        self._reuse_btn.clicked.connect(self._reuse_selected)
        row1.addWidget(self._reuse_btn)
        bl.addLayout(row1)
        row2 = QHBoxLayout()
        open_btn = QPushButton("📂 Open Folder")
        open_btn.setObjectName("secondary_btn")
        open_btn.clicked.connect(self._open_folder)
        row2.addWidget(open_btn)
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self.refresh)
        row2.addWidget(refresh_btn)
        archive_btn = QPushButton("📦 Archive")
        archive_btn.setObjectName("secondary_btn")
        archive_btn.setToolTip("Move the selected video(s) to the Archive folder (set in Settings)")
        archive_btn.clicked.connect(self._archive_selected)
        row2.addWidget(archive_btn)
        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("cancel_btn")
        del_btn.setToolTip("Delete the selected video file(s) — goes to the Recycle Bin (Del)")
        del_btn.clicked.connect(self._delete_selected)
        row2.addWidget(del_btn)
        row2.addStretch()
        bl.addLayout(row2)
        rl.addWidget(btn_group)

        info_group = QGroupBox("Selected video")
        il = QVBoxLayout(info_group)
        il.setSpacing(4)
        self._info = QLabel("Nothing selected")
        self._info.setWordWrap(True)
        self._info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        il.addWidget(self._info)
        rl.addWidget(info_group)

        made_group = QGroupBox("Produced by")
        ml = QVBoxLayout(made_group)
        ml.setSpacing(4)
        self._made_lbl = QLabel("")
        self._made_lbl.setWordWrap(True)
        self._made_lbl.setObjectName("status_dim")
        ml.addWidget(self._made_lbl)
        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText(
            "Select one video to see the prompt, LoRAs, seed and length it was generated with "
            "(from the workflow's prompt history).")
        ml.addWidget(self._details, stretch=1)
        rl.addWidget(made_group, stretch=1)

        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([1000, 520])
        lay.addWidget(split)

    # ------------------------------------------------------------------ #

    def effective_folder(self) -> str:
        return (self._cfg.get("library_dir", "") or "").strip() or (self._cfg.get("output_dir", "") or "").strip()

    def set_folder(self, folder: str):
        self.browser.set_folder(folder)

    def refresh(self):
        self.browser.refresh()

    def shutdown(self):
        self.browser.shutdown()

    def _on_folder_changed(self, folder: str):
        self._cfg.set("library_dir", folder)
        self._cfg.save()
        self.folder_changed.emit(folder)

    # ------------------------------------------------------------------ #

    def _selected(self) -> list[Path]:
        return self.browser.selected_paths()

    def _play_selected(self):
        paths = self._selected()
        if paths:
            self.play_requested.emit([str(p) for p in paths])

    def _send_selected(self):
        paths = self._selected()
        if paths:
            self.send_to_extend.emit(paths[0])

    def _reuse_selected(self):
        paths = self._selected()
        if len(paths) != 1 or self._detail_hit is None:
            return
        p = paths[0]
        if not p.exists():
            self._detail_hit = None
            self._reuse_btn.setEnabled(False)
            QMessageBox.information(
                self, "Reuse settings", f"{p.name} is no longer on disk — rescanning the Library.")
            self.refresh()
            return
        wf_path, entry = self._detail_hit
        self.reuse_requested.emit(p, wf_path, entry)

    def _open_folder(self):
        folder = self.browser.folder
        if folder and Path(folder).is_dir():
            os.startfile(folder)

    def _delete_selected(self):
        paths = self._selected()
        if not paths:
            return
        names = "\n".join(p.name for p in paths[:8]) + ("\n…" if len(paths) > 8 else "")
        ans = QMessageBox.question(
            self, "Delete video" + ("s" if len(paths) > 1 else ""),
            f"Send {len(paths)} file{'s' if len(paths) > 1 else ''} to the Recycle Bin?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.browser.deleting.emit(paths)
        root = Path(self.browser.folder) if self.browser.folder else None
        caches: list[Path] = []
        for p in paths:
            caches += thumbnail_caches(p, root)
        _n, errors, _recycled = delete_paths(paths + caches)
        if errors:
            QMessageBox.warning(self, "Delete", "Some files could not be deleted:\n" + "\n".join(errors))
        self.refresh()

    def _archive_selected(self):
        paths = self._selected()
        if not paths:
            return
        archive_dir = (self._cfg.get("archive_dir", "") or "").strip()
        if not archive_dir:
            QMessageBox.information(
                self, "Archive", "Set an Archive folder in Settings first (Folders → Archive).")
            return
        names = "\n".join(p.name for p in paths[:8]) + ("\n…" if len(paths) > 8 else "")
        ans = QMessageBox.question(
            self, "Archive video" + ("s" if len(paths) > 1 else ""),
            f"Move {len(paths)} file{'s' if len(paths) > 1 else ''} to the archive folder?\n\n"
            f"{names}\n\n→ {archive_dir}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.browser.deleting.emit(paths)   # close any player holding these files before they move
        root = Path(self.browser.folder) if self.browser.folder else None
        caches: list[Path] = []
        for p in paths:
            caches += thumbnail_caches(p, root)
        _moved, errors = archive_paths(paths, Path(archive_dir))
        if caches:
            delete_paths(caches)            # purge the cache so the grid never shows a stale tile
        if errors:
            QMessageBox.warning(self, "Archive", "Some files could not be archived:\n" + "\n".join(errors))
        gone = [p for p in paths if not p.exists()]
        if gone:
            self.browser.deleted.emit(gone)
        self.refresh()

    # ------------------------------------------------------------------ #

    def _on_loaded(self, _n: int):
        self._rebuild_date_values()
        self._apply_filter()

    @staticmethod
    def _date_key(ts: float, mode: str) -> str:
        d = datetime.fromtimestamp(ts)
        return {"year": d.strftime("%Y"), "month": d.strftime("%Y-%m"), "day": d.strftime("%Y-%m-%d")}.get(mode, "")

    @staticmethod
    def _item_ctime(item) -> float:
        try:
            return Path(item.data(Qt.ItemDataRole.UserRole)).stat().st_ctime
        except OSError:
            return 0.0

    def _rebuild_date_values(self):
        mode = self._date_mode.currentData()
        prev = self._date_value.currentData()
        grid = self.browser.grid
        self._date_value.blockSignals(True)
        self._date_value.clear()
        if mode == "all":
            self._date_value.setEnabled(False)
            self._date_value.addItem("—", "")
        else:
            self._date_value.setEnabled(True)
            counts: dict[str, int] = {}
            for i in range(grid.count()):
                k = self._date_key(self._item_ctime(grid.item(i)), mode)
                if k:
                    counts[k] = counts.get(k, 0) + 1
            for k in sorted(counts, reverse=True):
                self._date_value.addItem(f"{k}  ({counts[k]})", k)
            idx = self._date_value.findData(prev) if prev else -1
            self._date_value.setCurrentIndex(idx if idx >= 0 else 0)
        self._date_value.blockSignals(False)

    def _on_date_mode_changed(self, _i):
        self._rebuild_date_values()
        self._apply_filter()

    def _apply_filter(self, *_):
        query = self._search.text().strip().lower()
        mode = self._date_mode.currentData()
        dval = self._date_value.currentData() if mode and mode != "all" else ""
        grid = self.browser.grid
        shown = 0
        for i in range(grid.count()):
            item = grid.item(i)
            ok = (not query or query in item.text().lower())
            if ok and dval:
                ok = self._date_key(self._item_ctime(item), mode) == dval
            item.setHidden(not ok)
            if ok:
                shown += 1
        total = grid.count()
        self._filter_status.setText("" if shown == total else f"{shown} of {total} shown")

    # ------------------------------------------------------------------ #

    def _update_details(self):
        paths = self._selected()
        if not paths:
            self._info.setText("Nothing selected")
            self._made_lbl.setText("")
            self._details.setPlainText("")
            self._detail_hit = None
            self._reuse_btn.setEnabled(False)
            return
        if len(paths) > 1:
            total = 0
            for p in paths:
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
            self._info.setText(f"{len(paths)} videos selected  ·  {_fmt_size(total)}")
            self._made_lbl.setText("")
            self._details.setPlainText("")
            self._detail_hit = None
            self._reuse_btn.setEnabled(False)
            return
        p = paths[0]
        try:
            size = _fmt_size(p.stat().st_size)
        except OSError:
            size = "?"
        props = probe(self._ffmpeg_getter(), p)
        bits = [f"<b>{p.name}</b>", size]
        if props.width and props.height:
            bits.append(f"{props.width}×{props.height}")
        if props.fps:
            bits.append(f"{props.fps:g} fps")
        if props.duration:
            bits.append(_fmt_dur(props.duration))
        bits.append("audio" if props.has_audio else "no audio")
        self._info.setText("  ·  ".join(bits))

        wf_dir = Path((self._cfg.get("workflow_dir", "") or "").strip())
        hit = find_entry_for_result(wf_dir, p.name) if str(wf_dir) else None
        self._detail_hit = hit
        self._reuse_btn.setEnabled(hit is not None)
        if hit is None:
            self._made_lbl.setText("No history entry names this file (older run, renamed, or made elsewhere).")
            self._details.setPlainText("")
            return
        wf_path, entry = hit
        try:
            rel = wf_path.relative_to(wf_dir).as_posix()
        except ValueError:
            rel = wf_path.name
        self._made_lbl.setText(f"{rel}   ·   {entry.get('timestamp', '?')}")
        self._details.setPlainText(format_entry(entry))
        self._details.setStyleSheet(f"color: {COLORS['fg_primary']};")
