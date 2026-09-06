"""Library tab: browse finished videos (the Output folder by default),
play them, delete them, send one back to the Extend tab, and see the
prompt + settings that produced each one (from the prompt history)."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)

from config import ConfigManager
from file_ops import delete_paths, thumbnail_caches
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
    folder_changed = pyqtSignal(str)

    def __init__(self, config: ConfigManager, ffmpeg_getter, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._ffmpeg_getter = ffmpeg_getter

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
        split.addWidget(self.browser)

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

    # ------------------------------------------------------------------ #

    def _update_details(self):
        paths = self._selected()
        if not paths:
            self._info.setText("Nothing selected")
            self._made_lbl.setText("")
            self._details.setPlainText("")
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
