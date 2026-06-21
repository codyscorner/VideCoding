"""Multi-Source tab — run the same copy template across N source folders in sequence."""

import os
import logging
import threading
import queue
import time
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QProgressBar, QListWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer

from config import ConfigManager
from file_operations import FileCopier, FileValidator
from folder_organization import FolderStructure, FolderOrganizer
from ui.styles import COLORS


_SHOW_PREFIXES = (
    "Error", "Copied (large):", "Path too long", "Found ", "Scanning",
    "Reading", "Gathering", "Checking", "Starting", "Sorting",
    "Duplicate found:", "Operation cancelled", "Start:",
    "Retry ", "CHECKSUM",
)


class MultiSourceTab(QWidget):
    def __init__(self, config_manager: ConfigManager, logger):
        super().__init__()
        self._config = config_manager
        self._logger = logger
        self._cancel_requested = False
        self._is_running = False
        self._progress_queue: queue.Queue = queue.Queue()
        self._completed_copied = 0
        self._completed_skipped = 0
        self._completed_errors = 0

        self._build_ui()
        self._load_config()

        self._poll_timer = QTimer()
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._poll_queue)

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # ── Source List ──────────────────────────────────────────────────────
        src_hdr = QHBoxLayout()
        src_lbl = QLabel("Source Folders")
        src_lbl.setObjectName("section_label")
        src_hdr.addWidget(src_lbl)
        src_hdr.addStretch()
        btn_add = QPushButton("＋ Add Folder")
        btn_add.setObjectName("preview_btn")
        btn_add.setFixedWidth(130)
        btn_add.clicked.connect(self._add_source)
        btn_remove = QPushButton("Remove")
        btn_remove.setObjectName("preview_btn")
        btn_remove.setFixedWidth(90)
        btn_remove.clicked.connect(self._remove_source)
        btn_clear = QPushButton("Clear All")
        btn_clear.setObjectName("preview_btn")
        btn_clear.setFixedWidth(90)
        btn_clear.clicked.connect(self._clear_sources)
        src_hdr.addWidget(btn_add)
        src_hdr.addWidget(btn_remove)
        src_hdr.addWidget(btn_clear)
        layout.addLayout(src_hdr)

        self.source_list = QListWidget()
        self.source_list.setMinimumHeight(130)
        self.source_list.setMaximumHeight(170)
        layout.addWidget(self.source_list)

        hint_src = QLabel("Add each drive or folder you want to scan. The same template runs across all of them in order.")
        hint_src.setObjectName("dim_label")
        layout.addWidget(hint_src)

        # ── Destination ──────────────────────────────────────────────────────
        layout.addWidget(QLabel("Destination Folder:"))
        dst_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        dst_browse = QPushButton("Browse...")
        dst_browse.setMinimumWidth(100)
        dst_browse.clicked.connect(self._browse_dest)
        dst_row.addWidget(self.dest_edit)
        dst_row.addWidget(dst_browse)
        layout.addLayout(dst_row)

        # ── File Mask ────────────────────────────────────────────────────────
        self._presets = {
            "-- Select Preset --": "",
            "All Files": "*.*",
            "Images":    "*.jpg, *.jpeg, *.png, *.gif, *.bmp, *.tiff, *.tif, *.webp, *.svg, *.ico, *.raw, *.heic, *.heif",
            "Videos":    "*.mp4, *.avi, *.mkv, *.mov, *.wmv, *.flv, *.webm, *.m4v, *.mpeg, *.mpg, *.3gp, *.ts",
            "Audio":     "*.mp3, *.wav, *.flac, *.aac, *.ogg, *.wma, *.m4a, *.opus, *.aiff, *.alac",
            "Documents": "*.pdf, *.doc, *.docx, *.xls, *.xlsx, *.ppt, *.pptx, *.txt, *.rtf, *.odt, *.ods, *.odp",
            "Archives":  "*.zip, *.rar, *.7z, *.tar, *.gz, *.bz2, *.xz, *.iso, *.cab",
            "Code":      "*.py, *.js, *.ts, *.html, *.css, *.java, *.cpp, *.c, *.h, *.cs, *.php, *.rb, *.go, *.rs, *.swift",
            "Data":      "*.json, *.xml, *.csv, *.yaml, *.yml, *.sql, *.db, *.sqlite, *.mdb",
        }

        mask_row = QHBoxLayout()
        mask_row.addWidget(QLabel("File Mask:"))
        mask_row.addSpacing(20)
        mask_row.addWidget(QLabel("Presets:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self._presets.keys()))
        self.preset_combo.setFixedWidth(160)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        mask_row.addWidget(self.preset_combo)
        mask_row.addStretch()
        layout.addLayout(mask_row)

        self.ext_edit = QLineEdit()
        layout.addWidget(self.ext_edit)
        hint_mask = QLabel("Example: *.*  or  *.jpg, *.png  or  oct*.*  or  .pdf")
        hint_mask.setObjectName("dim_label")
        layout.addWidget(hint_mask)

        # ── Copy Options ─────────────────────────────────────────────────────
        opts_lbl = QLabel("Copy Options")
        opts_lbl.setObjectName("section_label")
        layout.addWidget(opts_lbl)

        self.recursive_check = QCheckBox("Search subfolders recursively (include all files from nested folders)")
        self.preserve_check = QCheckBox("Preserve original folder structure")
        self.number_check = QCheckBox("Number duplicate files (e.g., file_001.jpg, file_002.jpg)")
        self.incremental_check = QCheckBox("Incremental backup — skip files that already exist unchanged at destination (size + date match)")
        self.verify_check = QCheckBox("Verify copied files with checksum (MD5) — slower but confirms file integrity")
        self.preserve_check.stateChanged.connect(self._on_preserve_changed)
        layout.addWidget(self.recursive_check)
        layout.addWidget(self.preserve_check)
        layout.addWidget(self.number_check)
        layout.addWidget(self.incremental_check)
        layout.addWidget(self.verify_check)

        # ── File Filters ─────────────────────────────────────────────────────
        filter_lbl = QLabel("File Filters")
        filter_lbl.setObjectName("section_label")
        layout.addWidget(filter_lbl)

        self.size_check = QCheckBox("Filter by file size:")
        self.size_check.stateChanged.connect(self._on_size_filter_changed)
        layout.addWidget(self.size_check)
        self.size_widget = QWidget()
        size_row = QHBoxLayout(self.size_widget)
        size_row.setContentsMargins(20, 0, 0, 0)
        size_row.addWidget(QLabel("Min:"))
        self.min_size_edit = QLineEdit("0")
        self.min_size_edit.setFixedWidth(80)
        size_row.addWidget(self.min_size_edit)
        size_row.addWidget(QLabel("Max:"))
        self.max_size_edit = QLineEdit()
        self.max_size_edit.setFixedWidth(80)
        size_row.addWidget(self.max_size_edit)
        size_row.addWidget(QLabel("Unit:"))
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["B", "KB", "MB", "GB"])
        self.unit_combo.setFixedWidth(60)
        size_row.addWidget(self.unit_combo)
        size_row.addStretch()
        layout.addWidget(self.size_widget)
        self.size_widget.setVisible(False)

        self.date_check = QCheckBox("Filter by file age:")
        self.date_check.stateChanged.connect(self._on_date_filter_changed)
        layout.addWidget(self.date_check)
        self.date_widget = QWidget()
        date_row = QHBoxLayout(self.date_widget)
        date_row.setContentsMargins(20, 0, 0, 0)
        date_row.addWidget(QLabel("Modified within last:"))
        self.days_edit = QLineEdit("30")
        self.days_edit.setFixedWidth(80)
        date_row.addWidget(self.days_edit)
        date_row.addWidget(QLabel("days"))
        date_row.addStretch()
        layout.addWidget(self.date_widget)
        self.date_widget.setVisible(False)

        # ── Folder Organization ──────────────────────────────────────────────
        self.folder_org_widget = QWidget()
        fo_layout = QVBoxLayout(self.folder_org_widget)
        fo_layout.setContentsMargins(0, 0, 0, 0)
        fo_lbl = QLabel("Folder Organization (when not preserving structure)")
        fo_lbl.setObjectName("section_label")
        fo_layout.addWidget(fo_lbl)
        fo_layout.addWidget(QLabel("Organize into:"))
        self.folder_combo = QComboBox()
        self.folder_combo.addItems(["flat", "year", "year_month", "year_month_day", "date", "month"])
        self.folder_combo.setFixedWidth(200)
        self.folder_combo.currentTextChanged.connect(self._update_folder_example)
        fo_layout.addWidget(self.folder_combo)
        self.folder_example_label = QLabel("")
        self.folder_example_label.setObjectName("dim_label")
        fo_layout.addWidget(self.folder_example_label)
        layout.addWidget(self.folder_org_widget)
        self._update_folder_example()
        self._on_preserve_changed()

        # ── Action Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Run All Sources")
        self.run_btn.clicked.connect(self._start_run)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_run)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Progress ─────────────────────────────────────────────────────────
        self.source_progress_label = QLabel("Ready — add source folders and click Run All Sources")
        self.source_progress_label.setObjectName("dim_label")
        layout.addWidget(self.source_progress_label)

        self.source_progress = QProgressBar()
        self.source_progress.setRange(0, 100)
        layout.addWidget(self.source_progress)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Current File:"))
        self.file_label = QLabel("")
        self.file_label.setObjectName("dim_label")
        file_row.addWidget(self.file_label, stretch=1)
        layout.addLayout(file_row)

        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        layout.addWidget(self.file_progress)

        counters_row = QHBoxLayout()
        counters_row.addWidget(QLabel("Total Copied:"))
        self.copied_label = QLabel("0")
        self.copied_label.setObjectName("section_label")
        counters_row.addWidget(self.copied_label)
        counters_row.addSpacing(20)
        counters_row.addWidget(QLabel("Skipped:"))
        self.skipped_label = QLabel("0")
        self.skipped_label.setObjectName("section_label")
        counters_row.addWidget(self.skipped_label)
        counters_row.addSpacing(20)
        counters_row.addWidget(QLabel("Errors:"))
        self.errors_label = QLabel("0")
        self.errors_label.setObjectName("section_label")
        counters_row.addWidget(self.errors_label)
        counters_row.addStretch()
        layout.addLayout(counters_row)

        # ── Status Log ───────────────────────────────────────────────────────
        status_hdr = QHBoxLayout()
        status_hdr.addWidget(QLabel("Status (per-source results & errors):"))
        status_hdr.addStretch()
        clear_lbl = QLabel("[Clear]")
        clear_lbl.setObjectName("clear_label")
        clear_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_lbl.mousePressEvent = lambda e: self.status_list.clear()
        status_hdr.addWidget(clear_lbl)
        layout.addLayout(status_hdr)

        self.status_list = QListWidget()
        self.status_list.setMinimumHeight(130)
        self.status_list.setMaximumHeight(200)
        layout.addWidget(self.status_list)

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_config(self):
        for path in self._config.get("multi_source_list", []):
            self.source_list.addItem(path)
        self.dest_edit.setText(self._config.get("multi_dest_folder", ""))
        self.ext_edit.setText(self._config.get("multi_extension", ""))
        self.recursive_check.setChecked(self._config.get("multi_recursive", True))
        self.preserve_check.setChecked(self._config.get("multi_preserve_structure", True))
        self.number_check.setChecked(self._config.get("multi_number_duplicates", True))
        self.incremental_check.setChecked(self._config.get("multi_incremental", False))
        self.verify_check.setChecked(self._config.get("multi_verify_checksum", False))
        self.folder_combo.setCurrentText(self._config.get("multi_folder_structure", "flat"))
        self.size_check.setChecked(self._config.get("multi_enable_size_filter", False))
        self.date_check.setChecked(self._config.get("multi_enable_date_filter", False))
        self.min_size_edit.setText(str(self._config.get("multi_min_size", "0")))
        self.max_size_edit.setText(str(self._config.get("multi_max_size", "")))
        self.unit_combo.setCurrentText(self._config.get("multi_size_unit", "MB"))
        self.days_edit.setText(str(self._config.get("multi_days_old", "30")))
        self._on_preserve_changed()

    def _save_config(self):
        sources = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        self._config.set("multi_source_list", sources)
        self._config.set("multi_dest_folder", self.dest_edit.text().strip())
        self._config.set("multi_extension", self.ext_edit.text().strip())
        self._config.set("multi_recursive", self.recursive_check.isChecked())
        self._config.set("multi_preserve_structure", self.preserve_check.isChecked())
        self._config.set("multi_number_duplicates", self.number_check.isChecked())
        self._config.set("multi_incremental", self.incremental_check.isChecked())
        self._config.set("multi_verify_checksum", self.verify_check.isChecked())
        self._config.set("multi_folder_structure", self.folder_combo.currentText())
        self._config.set("multi_enable_size_filter", self.size_check.isChecked())
        self._config.set("multi_enable_date_filter", self.date_check.isChecked())
        self._config.set("multi_min_size", self.min_size_edit.text())
        self._config.set("multi_max_size", self.max_size_edit.text())
        self._config.set("multi_size_unit", self.unit_combo.currentText())
        self._config.set("multi_days_old", self.days_edit.text())
        self._config.save()

    # ── Source List Management ───────────────────────────────────────────────

    def _add_source(self):
        last = self.source_list.item(self.source_list.count() - 1)
        start = last.text() if last and os.path.isdir(last.text()) else ""
        folder = QFileDialog.getExistingDirectory(self, "Add Source Folder", start)
        if not folder:
            return
        existing = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        if folder in existing:
            QMessageBox.information(self, "Duplicate", "That folder is already in the list.")
            return
        self.source_list.addItem(folder)
        self._save_config()

    def _remove_source(self):
        row = self.source_list.currentRow()
        if row >= 0:
            self.source_list.takeItem(row)
            self._save_config()

    def _clear_sources(self):
        if self.source_list.count() == 0:
            return
        reply = QMessageBox.question(
            self, "Clear Sources", "Remove all source folders from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.source_list.clear()
            self._save_config()

    # ── Slot Handlers ────────────────────────────────────────────────────────

    def _browse_dest(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)

    def _on_preset_selected(self, text: str):
        value = self._presets.get(text, "")
        if value:
            self.ext_edit.setText(value)

    def _on_preserve_changed(self):
        self.folder_org_widget.setVisible(not self.preserve_check.isChecked())

    def _on_size_filter_changed(self):
        self.size_widget.setVisible(self.size_check.isChecked())

    def _on_date_filter_changed(self):
        self.date_widget.setVisible(self.date_check.isChecked())

    def _update_folder_example(self):
        try:
            structure = FolderStructure(self.folder_combo.currentText())
            example = FolderOrganizer.get_folder_structure_example(structure)
            self.folder_example_label.setText(f"Example: {example}")
        except Exception:
            self.folder_example_label.setText("")

    def _add_status(self, message: str):
        if self.status_list.count() >= 1000:
            self.status_list.takeItem(0)
        self.status_list.addItem(message)
        self.status_list.scrollToBottom()

    # ── Validation ───────────────────────────────────────────────────────────

    def _build_run_options(self) -> dict | None:
        sources = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        dest = self.dest_edit.text().strip()
        extension = self.ext_edit.text().strip()

        if not sources:
            QMessageBox.critical(self, "Error", "Please add at least one source folder.")
            return None
        if not dest:
            QMessageBox.critical(self, "Error", "Please select a destination folder.")
            return None
        if not extension:
            QMessageBox.critical(self, "Error", "Please enter a file mask (e.g. *.jpg or *.*).")
            return None

        missing = [s for s in sources if not os.path.isdir(s)]
        if missing:
            QMessageBox.critical(self, "Error",
                "The following source folders do not exist:\n" + "\n".join(missing))
            return None

        if not os.path.isdir(dest):
            try:
                os.makedirs(dest)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot create destination folder:\n{e}")
                return None

        min_size_bytes = max_size_bytes = max_days_old = None

        if self.size_check.isChecked():
            try:
                unit_mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                mult = unit_mult.get(self.unit_combo.currentText(), 1024**2)
                min_val = self.min_size_edit.text().strip()
                if min_val:
                    min_size_bytes = float(min_val) * mult
                max_val = self.max_size_edit.text().strip()
                if max_val:
                    max_size_bytes = float(max_val) * mult
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid size filter values.")
                return None

        if self.date_check.isChecked():
            try:
                days_val = self.days_edit.text().strip()
                if days_val:
                    max_days_old = int(days_val)
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid date filter value.")
                return None

        return {
            'sources': sources,
            'dest_folder': dest,
            'extension': extension,
            'preserve_structure': self.preserve_check.isChecked(),
            'number_duplicates': self.number_check.isChecked(),
            'recursive_search': self.recursive_check.isChecked(),
            'folder_structure': self.folder_combo.currentText(),
            'min_size_bytes': min_size_bytes,
            'max_size_bytes': max_size_bytes,
            'max_days_old': max_days_old,
            'verify_checksum': self.verify_check.isChecked(),
            'incremental': self.incremental_check.isChecked(),
        }

    # ── Run / Cancel ─────────────────────────────────────────────────────────

    def _start_run(self):
        options = self._build_run_options()
        if options is None:
            return

        self._save_config()
        self.status_list.clear()
        self._is_running = True
        self._cancel_requested = False
        self._completed_copied = 0
        self._completed_skipped = 0
        self._completed_errors = 0
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.source_progress.setValue(0)
        self.file_progress.setValue(0)
        self.file_label.setText("")
        self.copied_label.setText("0")
        self.skipped_label.setText("0")
        self.errors_label.setText("0")
        n = len(options['sources'])
        self.source_progress_label.setText(f"Starting — {n} source{'s' if n != 1 else ''} queued…")

        threading.Thread(target=self._worker, args=(options,), daemon=True).start()
        self._poll_timer.start()

    def _cancel_run(self):
        if self._is_running:
            self._cancel_requested = True
            self.cancel_btn.setEnabled(False)
            self.source_progress_label.setText("Cancelling after current file…")
            self._add_status("Cancellation requested — stopping after current file")

    # ── Worker Thread ────────────────────────────────────────────────────────

    def _worker(self, options: dict):
        sources = options['sources']
        total_sources = len(sources)
        grand_copied = grand_skipped = grand_errors = 0
        start_time = time.time()

        try:
            folder_structure = FolderStructure(options['folder_structure'])
        except ValueError:
            folder_structure = FolderStructure.FLAT

        for src_idx, source in enumerate(sources, 1):
            if self._cancel_requested:
                break

            self._queue_msg('source_start', {
                'index': src_idx, 'total': total_sources, 'path': source,
            })

            try:
                def _status_cb(msg, _i=src_idx, _n=total_sources):
                    if any(msg.startswith(p) for p in _SHOW_PREFIXES):
                        self._queue_msg('status', f"[{_i}/{_n}] {msg}")

                copier = FileCopier(
                    status_callback=_status_cb,
                    folder_structure=folder_structure,
                    number_duplicates=options['number_duplicates'],
                    progress_callback=lambda cur, tot, fname, fprog, _i=src_idx, _n=total_sources: (
                        self._queue_msg('progress', {
                            'source_idx': _i, 'source_total': _n,
                            'current': cur, 'total': tot,
                            'filename': fname, 'file_progress': fprog,
                        })
                    ),
                    cancel_check=lambda: self._cancel_requested,
                    counters_callback=lambda c, s, e: self._queue_msg(
                        'source_counters', {'copied': c, 'skipped': s, 'errors': e}
                    ),
                    verify_checksum=options.get('verify_checksum', False),
                    incremental=options.get('incremental', False),
                )

                results = copier.copy_files(
                    source, options['dest_folder'], options['extension'],
                    options['preserve_structure'], options['recursive_search'],
                    min_size_bytes=options.get('min_size_bytes'),
                    max_size_bytes=options.get('max_size_bytes'),
                    max_days_old=options.get('max_days_old'),
                )

                if self._cancel_requested:
                    # Count partial results before breaking
                    c = sum(1 for r in results if r.success and r.destination_file is not None)
                    s = sum(1 for r in results if r.success and r.destination_file is None)
                    e = sum(1 for r in results if not r.success)
                    grand_copied += c
                    grand_skipped += s
                    grand_errors += e
                    break

                copied = sum(1 for r in results if r.success and r.destination_file is not None)
                skipped = sum(1 for r in results if r.success and r.destination_file is None)
                errors = sum(1 for r in results if not r.success)
                grand_copied += copied
                grand_skipped += skipped
                grand_errors += errors

                self._queue_msg('source_complete', {
                    'index': src_idx, 'total': total_sources, 'path': source,
                    'copied': copied, 'skipped': skipped, 'errors': errors,
                    'grand_copied': grand_copied,
                    'grand_skipped': grand_skipped,
                    'grand_errors': grand_errors,
                })

            except Exception as e:
                self._logger.error(f"Multi-source error on {source}: {e}")
                self._queue_msg('status', f"[{src_idx}/{total_sources}] ERROR: {e}")
                grand_errors += 1
                self._queue_msg('source_complete', {
                    'index': src_idx, 'total': total_sources, 'path': source,
                    'copied': 0, 'skipped': 0, 'errors': 1,
                    'grand_copied': grand_copied,
                    'grand_skipped': grand_skipped,
                    'grand_errors': grand_errors,
                })

        end_time = time.time()

        if self._cancel_requested:
            self._queue_msg('all_cancelled', {
                'copied': grand_copied, 'skipped': grand_skipped, 'errors': grand_errors,
            })
        else:
            self._queue_msg('all_complete', {
                'copied': grand_copied, 'skipped': grand_skipped, 'errors': grand_errors,
                'start_time': start_time, 'end_time': end_time,
            })

    # ── Queue / Progress Polling ─────────────────────────────────────────────

    def _queue_msg(self, msg_type: str, data):
        self._progress_queue.put((msg_type, data))

    def _poll_queue(self):
        try:
            while True:
                try:
                    msg_type, data = self._progress_queue.get_nowait()

                    if msg_type == 'status':
                        self._add_status(data)

                    elif msg_type == 'source_start':
                        idx, total, path = data['index'], data['total'], data['path']
                        pct = int((idx - 1) / total * 100)
                        self.source_progress.setValue(pct)
                        self.source_progress_label.setText(
                            f"Source  {idx} / {total}  —  {path}"
                        )
                        self.file_label.setText("")
                        self.file_progress.setValue(0)
                        self._add_status(f"── [{idx}/{total}] {path}")

                    elif msg_type == 'source_counters':
                        # Live per-file counters: base (completed sources) + current source running counts
                        self.copied_label.setText(str(self._completed_copied + data['copied']))
                        self.skipped_label.setText(str(self._completed_skipped + data['skipped']))
                        self.errors_label.setText(str(self._completed_errors + data['errors']))

                    elif msg_type == 'progress':
                        if data['file_progress'] >= 0:
                            self.file_progress.setValue(data['file_progress'])
                        cur, tot = data['current'], data['total']
                        label = data['filename']
                        if tot > 0:
                            label = f"{cur} / {tot}  —  {label}"
                        self.file_label.setText(label)

                    elif msg_type == 'source_complete':
                        idx, total = data['index'], data['total']
                        path = data['path']
                        c, s, e = data['copied'], data['skipped'], data['errors']
                        self.source_progress.setValue(int(idx / total * 100))
                        self._completed_copied = data['grand_copied']
                        self._completed_skipped = data['grand_skipped']
                        self._completed_errors = data['grand_errors']
                        self.copied_label.setText(str(self._completed_copied))
                        self.skipped_label.setText(str(self._completed_skipped))
                        self.errors_label.setText(str(self._completed_errors))
                        status_line = f"  ✓ [{idx}/{total}]  copied={c}  skipped={s}  errors={e}  —  {path}"
                        self._add_status(status_line)

                    elif msg_type == 'all_complete':
                        self._poll_timer.stop()
                        self._on_all_complete(data)
                        return

                    elif msg_type == 'all_cancelled':
                        self._poll_timer.stop()
                        self._on_all_cancelled(data)
                        return

                except queue.Empty:
                    break
        except Exception as exc:
            print(f"Multi-source queue poll error: {exc}")

    # ── Completion Handlers ──────────────────────────────────────────────────

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        ms = int((seconds % 1) * 100)
        total_s = int(seconds)
        hh = total_s // 3600
        mm = (total_s % 3600) // 60
        ss = total_s % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:02d}"

    def _on_all_complete(self, data: dict):
        self._is_running = False
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.source_progress.setValue(100)

        copied = data['copied']
        skipped = data['skipped']
        errors = data['errors']
        elapsed = data['end_time'] - data['start_time']
        elapsed_str = self._format_elapsed(elapsed)

        self.copied_label.setText(str(copied))
        self.skipped_label.setText(str(skipped))
        self.errors_label.setText(str(errors))
        self.source_progress_label.setText(f"All sources complete  —  Elapsed: {elapsed_str}")
        self._add_status(f"═══ All sources complete  —  Elapsed: {elapsed_str}  —  Copied: {copied}  Skipped: {skipped}  Errors: {errors} ═══")

        summary = f"Total Copied: {copied}\nTotal Skipped: {skipped}\nTotal Errors: {errors}\nElapsed: {elapsed_str}"
        if errors == 0 and copied > 0:
            QMessageBox.information(self, "Complete", summary)
        elif copied > 0:
            QMessageBox.warning(self, "Completed with errors",
                f"{summary}\n\nCheck the status log for details.")
        else:
            QMessageBox.information(self, "Complete",
                "No files were found to copy across all sources.\n\nCheck file mask and source folders.")

    def _on_all_cancelled(self, data: dict):
        self._is_running = False
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        copied, skipped, errors = data['copied'], data['skipped'], data['errors']
        self.copied_label.setText(str(copied))
        self.skipped_label.setText(str(skipped))
        self.errors_label.setText(str(errors))
        self.source_progress_label.setText("Cancelled")
        self._add_status(
            f"Operation cancelled  —  Copied: {copied}  Skipped: {skipped}  Errors: {errors}"
        )
        QMessageBox.information(
            self, "Cancelled",
            f"Operation cancelled.\n\nCopied so far: {copied}\nSkipped: {skipped}",
        )
