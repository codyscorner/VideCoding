"""Main window for Bulk File Randomizer"""

import os
import queue
import random
import string
import threading
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from config import ConfigManager
from renamer import copy_and_rename
from ui.styles import STYLESHEET

_CHARS = string.ascii_letters + string.digits


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, version: str):
        super().__init__()
        self.config = config
        self.version = version

        self._thread: threading.Thread | None = None
        self._queue: queue.Queue = queue.Queue()
        self._cancel = False
        self._running = False

        self.setWindowTitle(f"Bulk File Randomizer  (V-{version})")
        self.setMinimumSize(640, 560)
        self.resize(780, 660)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._load_config()

        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll)

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)

        root = QWidget()
        scroll.setWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(8)

        title = QLabel("Bulk File Randomizer")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Copy files into a subfolder with randomised names  ·  prefix_xxxxxxxxxx.ext")
        sub.setObjectName("subtitle_label")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        # Source folder
        lay.addWidget(QLabel("Source Folder:"))
        src_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        self.source_edit.textChanged.connect(self._update_preview)
        src_btn = QPushButton("Browse…")
        src_btn.setMinimumWidth(90)
        src_btn.clicked.connect(self._browse_source)
        src_row.addWidget(self.source_edit)
        src_row.addWidget(src_btn)
        lay.addLayout(src_row)

        # Prefix
        lay.addWidget(QLabel("Prefix  (used as subfolder name and file prefix):"))
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("e.g.  Fight")
        self.prefix_edit.textChanged.connect(self._update_preview)
        lay.addWidget(self.prefix_edit)

        # Preview
        self.preview_label = QLabel("")
        self.preview_label.setObjectName("preview_label")
        lay.addWidget(self.preview_label)

        # File mask
        mask_row = QHBoxLayout()
        mask_row.addWidget(QLabel("File Mask:"))
        mask_row.addSpacing(16)
        mask_row.addWidget(QLabel("Presets:"))
        self._presets = {
            "-- Select --":  "",
            "All Files":     "*.*",
            "Images":        "*.jpg, *.jpeg, *.png, *.gif, *.bmp, *.tiff, *.webp, *.heic",
            "Videos":        "*.mp4, *.avi, *.mkv, *.mov, *.wmv, *.webm, *.m4v",
            "Audio":         "*.mp3, *.wav, *.flac, *.aac, *.ogg, *.m4a",
            "Documents":     "*.pdf, *.doc, *.docx, *.txt, *.rtf",
        }
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self._presets.keys()))
        self.preset_combo.setFixedWidth(140)
        self.preset_combo.currentTextChanged.connect(self._on_preset)
        mask_row.addWidget(self.preset_combo)
        mask_row.addStretch()
        lay.addLayout(mask_row)

        self.mask_edit = QLineEdit()
        self.mask_edit.setPlaceholderText("e.g.  *.*  or  *.png, *.jpg")
        lay.addWidget(self.mask_edit)
        hint = QLabel("Separate multiple patterns with commas")
        hint.setObjectName("dim_label")
        lay.addWidget(hint)

        # Options
        opts_lbl = QLabel("Options")
        opts_lbl.setObjectName("section_label")
        lay.addWidget(opts_lbl)
        self.recursive_check = QCheckBox("Search subfolders recursively")
        lay.addWidget(self.recursive_check)

        # Action buttons
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Copy & Rename")
        self.run_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._request_cancel)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Progress
        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Progress:"))
        self.count_label = QLabel("")
        self.count_label.setObjectName("dim_label")
        prog_row.addWidget(self.count_label, stretch=1)
        lay.addLayout(prog_row)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        lay.addWidget(self.progress_bar)
        self.file_label = QLabel("Ready")
        self.file_label.setObjectName("dim_label")
        lay.addWidget(self.file_label)

        # Counters
        counter_row = QHBoxLayout()
        counter_row.addWidget(QLabel("Copied:"))
        self.copied_lbl = QLabel("0")
        self.copied_lbl.setObjectName("section_label")
        counter_row.addWidget(self.copied_lbl)
        counter_row.addSpacing(20)
        counter_row.addWidget(QLabel("Errors:"))
        self.errors_lbl = QLabel("0")
        self.errors_lbl.setObjectName("section_label")
        counter_row.addWidget(self.errors_lbl)
        counter_row.addStretch()
        lay.addLayout(counter_row)

        # Status log
        log_hdr = QHBoxLayout()
        log_hdr.addWidget(QLabel("Log:"))
        log_hdr.addStretch()
        clear_lbl = QLabel("[Clear]")
        clear_lbl.setObjectName("clear_label")
        clear_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_lbl.mousePressEvent = lambda _e: self.log_list.clear()
        log_hdr.addWidget(clear_lbl)
        lay.addLayout(log_hdr)
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(80)
        self.log_list.setMaximumHeight(160)
        lay.addWidget(self.log_list)
        self._log("Ready.")

    def _load_config(self):
        self.source_edit.setText(self.config.get("last_source_folder", ""))
        self.prefix_edit.setText(self.config.get("last_prefix", ""))
        self.mask_edit.setText(self.config.get("last_file_mask", "*.*"))
        self.recursive_check.setChecked(self.config.get("recursive_search", False))
        self._update_preview()

    # ---------------------------------------------------------------- slots --

    def _browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def _on_preset(self, text: str):
        value = self._presets.get(text, "")
        if value:
            self.mask_edit.setText(value)

    def _update_preview(self):
        prefix = self.prefix_edit.text().strip()
        source = self.source_edit.text().strip()
        if not prefix:
            self.preview_label.setText("")
            return
        sample = f"{''.join(random.choices(_CHARS, k=10))}"
        dest_path = f"{source}/{prefix}/" if source else f"<source>/{prefix}/"
        self.preview_label.setText(
            f"Output folder:  {dest_path}   ·   Example name:  {prefix}_{sample}.ext"
        )

    def _log(self, msg: str):
        if self.log_list.count() >= 500:
            self.log_list.takeItem(0)
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

    # ----------------------------------------------------------------- work --

    def _start(self):
        source = self.source_edit.text().strip()
        prefix = self.prefix_edit.text().strip()
        mask = self.mask_edit.text().strip()

        if not source:
            QMessageBox.critical(self, "Error", "Please select a source folder.")
            return
        if not os.path.isdir(source):
            QMessageBox.critical(self, "Error", f"Source folder not found:\n{source}")
            return
        if not prefix:
            QMessageBox.critical(self, "Error", "Please enter a prefix.")
            return
        if not prefix.replace("_", "").replace("-", "").isalnum():
            QMessageBox.warning(
                self, "Warning",
                "Prefix contains special characters.\nThe subfolder will be created with that exact name."
            )
        if not mask:
            mask = "*.*"

        masks = [m.strip() for m in mask.split(",") if m.strip()]

        self._cancel = False
        self._running = True
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.count_label.setText("")
        self.file_label.setText("")
        self.copied_lbl.setText("0")
        self.errors_lbl.setText("0")

        self.config.set("last_source_folder", source)
        self.config.set("last_prefix", prefix)
        self.config.set("last_file_mask", mask)
        self.config.set("recursive_search", self.recursive_check.isChecked())
        self.config.save()

        self._thread = threading.Thread(
            target=self._worker,
            args=(source, prefix, masks, self.recursive_check.isChecked()),
            daemon=True,
        )
        self._thread.start()
        self._timer.start()

    def _worker(self, source: str, prefix: str, masks: list, recursive: bool):
        try:
            start = time.time()
            self._q("log", f"Start — source: {source}  prefix: {prefix}")

            results = copy_and_rename(
                source_dir=Path(source),
                prefix=prefix,
                masks=masks,
                recursive=recursive,
                progress_cb=lambda i, t, n: self._q("progress", (i, t, n)),
                cancel_check=lambda: self._cancel,
            )

            copied = sum(1 for r in results if r.success)
            errors = sum(1 for r in results if not r.success)
            for r in results:
                if not r.success:
                    self._q("log", f"ERROR: {r.source.name} — {r.error}")

            elapsed = time.time() - start
            self._q("done", (copied, errors, elapsed))
        except Exception as exc:
            self._q("error", str(exc))

    def _q(self, kind: str, data):
        self._queue.put((kind, data))

    def _poll(self):
        try:
            while True:
                kind, data = self._queue.get_nowait()
                if kind == "progress":
                    i, total, name = data
                    if total > 0:
                        self.progress_bar.setValue(int(i / total * 100))
                        self.count_label.setText(f"{i} of {total}")
                    self.file_label.setText(name)
                elif kind == "log":
                    self._log(data)
                elif kind == "done":
                    self._timer.stop()
                    self._on_done(*data)
                    return
                elif kind == "error":
                    self._timer.stop()
                    self._on_error(data)
                    return
        except queue.Empty:
            pass

    def _request_cancel(self):
        self._cancel = True
        self.cancel_btn.setEnabled(False)
        self.file_label.setText("Cancelling…")
        self._log("Cancellation requested…")

    def _on_done(self, copied: int, errors: int, elapsed: float):
        self._running = False
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.copied_lbl.setText(str(copied))
        self.errors_lbl.setText(str(errors))
        m, s = divmod(int(elapsed), 60)
        self.file_label.setText("Done" if not self._cancel else "Cancelled")
        self._log(f"Finished — Copied: {copied}  Errors: {errors}  Time: {m:02d}:{s:02d}")
        if not self._cancel:
            if errors == 0:
                QMessageBox.information(self, "Done", f"Copied {copied} file(s) in {m:02d}:{s:02d}")
            else:
                QMessageBox.warning(self, "Done with errors",
                                    f"Copied: {copied}\nErrors: {errors}\n\nCheck the log for details.")

    def _on_error(self, msg: str):
        self._running = False
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._log(f"FATAL: {msg}")
        QMessageBox.critical(self, "Error", msg)
