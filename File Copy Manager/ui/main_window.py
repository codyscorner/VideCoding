"""Main window UI for File Copy Manager"""

import os
import logging
import threading
import queue
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QProgressBar, QListWidget,
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QFrame, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from config import ConfigManager
from file_operations import FileCopier
from folder_organization import FolderStructure, FolderOrganizer
from ui.styles import STYLESHEET, COLORS


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version

        self._copy_thread = None
        self._progress_queue = queue.Queue()
        self._cancel_requested = False
        self._is_copying = False

        self.setWindowTitle(f"File Copy Manager (V-{self.version})")
        self.setMinimumSize(900, 675)
        self.resize(1200, 900)
        self.setStyleSheet(STYLESHEET)

        log_path = Path(self.config.config_path).parent / "FileCopyManager.log"
        logging.basicConfig(
            filename=str(log_path), level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._logger = logging.getLogger("FileCopyManager")

        self._build_ui()
        self._load_config()

        self._poll_timer = QTimer()
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._poll_progress_queue)

    def _build_ui(self):
        # Scrollable central area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # Title
        title = QLabel("File Copy Manager")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Copy files with automatic numbering and folder organization")
        sub.setObjectName("subtitle_label")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        # Source folder
        layout.addWidget(QLabel("Source Folder:"))
        src_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        self.source_edit.setText(self.config.get("default_source_folder", ""))
        src_browse = QPushButton("Browse...")
        src_browse.setMinimumWidth(100)
        src_browse.clicked.connect(self._browse_source)
        src_row.addWidget(self.source_edit)
        src_row.addWidget(src_browse)
        layout.addLayout(src_row)

        # Dest folder
        layout.addWidget(QLabel("Destination Folder:"))
        dst_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        self.dest_edit.setText(self.config.get("default_destination_folder", ""))
        dst_browse = QPushButton("Browse...")
        dst_browse.setMinimumWidth(100)
        dst_browse.clicked.connect(self._browse_destination)
        dst_row.addWidget(self.dest_edit)
        dst_row.addWidget(dst_browse)
        layout.addLayout(dst_row)

        # File mask
        mask_header = QHBoxLayout()
        mask_header.addWidget(QLabel("File Mask:"))
        mask_header.addSpacing(20)
        mask_header.addWidget(QLabel("Presets:"))
        self.file_type_presets = {
            "-- Select Preset --": "",
            "Images":    "*.jpg, *.jpeg, *.png, *.gif, *.bmp, *.tiff, *.tif, *.webp, *.svg, *.ico, *.raw, *.heic, *.heif",
            "Videos":    "*.mp4, *.avi, *.mkv, *.mov, *.wmv, *.flv, *.webm, *.m4v, *.mpeg, *.mpg, *.3gp, *.ts",
            "Audio":     "*.mp3, *.wav, *.flac, *.aac, *.ogg, *.wma, *.m4a, *.opus, *.aiff, *.alac",
            "Documents": "*.pdf, *.doc, *.docx, *.xls, *.xlsx, *.ppt, *.pptx, *.txt, *.rtf, *.odt, *.ods, *.odp",
            "Archives":  "*.zip, *.rar, *.7z, *.tar, *.gz, *.bz2, *.xz, *.iso, *.cab",
            "Code":      "*.py, *.js, *.ts, *.html, *.css, *.java, *.cpp, *.c, *.h, *.cs, *.php, *.rb, *.go, *.rs, *.swift",
            "Data":      "*.json, *.xml, *.csv, *.yaml, *.yml, *.sql, *.db, *.sqlite, *.mdb",
        }
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.file_type_presets.keys()))
        self.preset_combo.setFixedWidth(160)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        mask_header.addWidget(self.preset_combo)
        mask_header.addStretch()
        layout.addLayout(mask_header)
        self.ext_edit = QLineEdit()
        self.ext_edit.setText(self.config.get("last_extension", ""))
        layout.addWidget(self.ext_edit)
        hint = QLabel("Example: *.jpg, *.png  or  oct*.*  or  .pdf")
        hint.setObjectName("dim_label")
        layout.addWidget(hint)

        # Copy options
        copy_section = QLabel("Copy Options")
        copy_section.setObjectName("section_label")
        layout.addWidget(copy_section)
        self.recursive_check = QCheckBox("Search subfolders recursively (include all files from nested folders)")
        self.preserve_check = QCheckBox("Preserve original folder structure")
        self.number_check = QCheckBox("Number duplicate files (e.g., file_001.jpg, file_002.jpg)")
        self.recursive_check.setChecked(self.config.get("recursive_search", True))
        self.preserve_check.setChecked(self.config.get("preserve_structure", True))
        self.number_check.setChecked(self.config.get("number_duplicates", True))
        self.preserve_check.stateChanged.connect(self._on_preserve_changed)
        layout.addWidget(self.recursive_check)
        layout.addWidget(self.preserve_check)
        layout.addWidget(self.number_check)

        # File filters
        filter_section = QLabel("File Filters")
        filter_section.setObjectName("section_label")
        layout.addWidget(filter_section)

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
        self.unit_combo.setCurrentText(self.config.get("size_unit", "MB"))
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
        self.days_edit = QLineEdit(str(self.config.get("days_old", "30")))
        self.days_edit.setFixedWidth(80)
        date_row.addWidget(self.days_edit)
        date_row.addWidget(QLabel("days"))
        date_row.addStretch()
        layout.addWidget(self.date_widget)
        self.date_widget.setVisible(False)

        # Folder organization
        self.folder_org_widget = QWidget()
        fo_layout = QVBoxLayout(self.folder_org_widget)
        fo_layout.setContentsMargins(0, 0, 0, 0)
        fo_lbl = QLabel("Folder Organization (when not preserving structure)")
        fo_lbl.setObjectName("section_label")
        fo_layout.addWidget(fo_lbl)
        fo_layout.addWidget(QLabel("Organize into:"))
        self.folder_combo = QComboBox()
        self.folder_combo.addItems(["flat", "year", "year_month", "year_month_day", "date", "month"])
        self.folder_combo.setCurrentText(self.config.get("folder_structure", "flat"))
        self.folder_combo.setFixedWidth(200)
        self.folder_combo.currentTextChanged.connect(self._update_folder_example)
        fo_layout.addWidget(self.folder_combo)
        self.folder_example_label = QLabel("")
        self.folder_example_label.setObjectName("dim_label")
        fo_layout.addWidget(self.folder_example_label)
        layout.addWidget(self.folder_org_widget)
        self._update_folder_example()
        self._on_preserve_changed()

        # Action buttons
        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Files")
        self.copy_btn.clicked.connect(self._start_copy)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_copy)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        layout.addWidget(QLabel("Overall Progress:"))
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        layout.addWidget(self.overall_progress)
        layout.addWidget(QLabel("Current File:"))
        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        layout.addWidget(self.file_progress)
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("dim_label")
        layout.addWidget(self.progress_label)

        counters_row = QHBoxLayout()
        counters_row.addWidget(QLabel("Copied:"))
        self.copied_label = QLabel("0")
        self.copied_label.setObjectName("section_label")
        counters_row.addWidget(self.copied_label)
        counters_row.addSpacing(20)
        counters_row.addWidget(QLabel("Skipped:"))
        self.skipped_label = QLabel("0")
        self.skipped_label.setObjectName("section_label")
        counters_row.addWidget(self.skipped_label)
        counters_row.addStretch()
        layout.addLayout(counters_row)

        # Status log
        layout.addWidget(QLabel("Status:"))
        self.status_list = QListWidget()
        self.status_list.setMinimumHeight(160)
        layout.addWidget(self.status_list, stretch=1)
        self._add_status("Ready to copy files...")

    def _load_config(self):
        self.size_check.setChecked(self.config.get("enable_size_filter", False))
        self.date_check.setChecked(self.config.get("enable_date_filter", False))
        self.min_size_edit.setText(str(self.config.get("min_size", "0")))
        self.max_size_edit.setText(str(self.config.get("max_size", "")))

    def _browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)
            self.config.set("default_source_folder", folder)
            self.config.save()
            self._add_status(f"Source folder selected: {folder}")

    def _browse_destination(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)
            self.config.set("default_destination_folder", folder)
            self.config.save()
            self._add_status(f"Destination folder selected: {folder}")

    def _on_preset_selected(self, text: str):
        value = self.file_type_presets.get(text, "")
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
        self.status_list.addItem(message)
        self.status_list.scrollToBottom()

    def _start_copy(self):
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        extension = self.ext_edit.text().strip()

        if not source:
            QMessageBox.critical(self, "Error", "Please select a source folder")
            return
        if not dest:
            QMessageBox.critical(self, "Error", "Please select a destination folder")
            return
        if not extension:
            QMessageBox.critical(self, "Error", "Please enter a file extension")
            return
        if source == dest:
            QMessageBox.critical(self, "Error", "Source and destination folders cannot be the same")
            return

        min_size_bytes = max_size_bytes = max_days_old = None

        if self.size_check.isChecked():
            try:
                unit_multiplier = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                multiplier = unit_multiplier.get(self.unit_combo.currentText(), 1024**2)
                min_val = self.min_size_edit.text().strip()
                if min_val:
                    min_size_bytes = float(min_val) * multiplier
                max_val = self.max_size_edit.text().strip()
                if max_val:
                    max_size_bytes = float(max_val) * multiplier
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid size filter values")
                return

        if self.date_check.isChecked():
            try:
                days_val = self.days_edit.text().strip()
                if days_val:
                    max_days_old = int(days_val)
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid date filter value")
                return

        self._is_copying = True
        self._cancel_requested = False
        self.copy_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.overall_progress.setValue(0)
        self.file_progress.setValue(0)
        self.progress_label.setText("Preparing...")
        self.copied_label.setText("0")
        self.skipped_label.setText("0")

        copy_options = {
            'source_folder': source, 'dest_folder': dest, 'extension': extension,
            'preserve_structure': self.preserve_check.isChecked(),
            'number_duplicates': self.number_check.isChecked(),
            'recursive_search': self.recursive_check.isChecked(),
            'folder_structure': self.folder_combo.currentText(),
            'min_size_bytes': min_size_bytes, 'max_size_bytes': max_size_bytes,
            'max_days_old': max_days_old,
        }

        self._copy_thread = threading.Thread(
            target=self._copy_worker, args=(copy_options,), daemon=True
        )
        self._copy_thread.start()
        self._poll_timer.start()

    def _copy_worker(self, options: dict):
        try:
            self._queue_msg('status', "Starting copy operation...")
            folder_structure = FolderStructure(options['folder_structure'])
            _live = [0, 0]

            def _status_cb(msg):
                if msg.startswith("Copied:") or msg.startswith("Duplicate found:"):
                    _live[0] += 1
                    self._queue_msg('counters', {'copied': _live[0], 'skipped': _live[1]})
                elif msg.startswith("Skipped"):
                    _live[1] += 1
                    self._queue_msg('counters', {'copied': _live[0], 'skipped': _live[1]})
                self._queue_msg('status', msg)

            copier = FileCopier(
                status_callback=_status_cb,
                folder_structure=folder_structure,
                number_duplicates=options['number_duplicates'],
                progress_callback=lambda cur, tot, fname, fprog: self._queue_msg(
                    'progress', {'current': cur, 'total': tot, 'filename': fname, 'file_progress': fprog}
                ),
                cancel_check=lambda: self._cancel_requested
            )
            results = copier.copy_files(
                options['source_folder'], options['dest_folder'], options['extension'],
                options['preserve_structure'], options['recursive_search'],
                min_size_bytes=options['min_size_bytes'],
                max_size_bytes=options['max_size_bytes'],
                max_days_old=options['max_days_old']
            )

            if self._cancel_requested:
                self._queue_msg('cancelled', None)
                return

            copied = sum(1 for r in results if r.success and r.destination_file is not None)
            skipped = sum(1 for r in results if r.success and r.destination_file is None)
            errors = sum(1 for r in results if not r.success)
            self._queue_msg('counters', {'copied': copied, 'skipped': skipped})
            self._queue_msg('complete', {'copied_count': copied, 'skipped_count': skipped, 'error_count': errors, 'options': options})

        except ValueError as e:
            self._queue_msg('error', {'type': 'validation', 'message': str(e)})
        except OSError as e:
            self._logger.error(f"FILE SYSTEM ERROR: {e}")
            self._queue_msg('error', {'type': 'filesystem', 'message': str(e)})
        except Exception as e:
            self._logger.error(f"UNEXPECTED ERROR: {e}")
            self._queue_msg('error', {'type': 'unexpected', 'message': str(e)})

    def _queue_msg(self, msg_type: str, data):
        self._progress_queue.put((msg_type, data))

    def _poll_progress_queue(self):
        try:
            while True:
                try:
                    msg_type, data = self._progress_queue.get_nowait()
                    if msg_type == 'status':
                        self._add_status(data)
                    elif msg_type == 'progress':
                        total = data['total']
                        if total > 0:
                            self.overall_progress.setValue(int((data['current'] / total) * 100))
                        self.file_progress.setValue(data['file_progress'])
                        self.progress_label.setText(f"Processing {data['current']}/{total}: {data['filename']}")
                    elif msg_type == 'counters':
                        self.copied_label.setText(str(data['copied']))
                        self.skipped_label.setText(str(data['skipped']))
                    elif msg_type == 'complete':
                        self._poll_timer.stop()
                        self._on_copy_complete(data)
                        return
                    elif msg_type == 'cancelled':
                        self._poll_timer.stop()
                        self._on_copy_cancelled()
                        return
                    elif msg_type == 'error':
                        self._poll_timer.stop()
                        self._on_copy_error(data)
                        return
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error in progress queue polling: {e}")

    def _on_copy_complete(self, data: dict):
        self._is_copying = False
        self.copy_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        opts = data['options']
        copied, skipped, errors = data['copied_count'], data['skipped_count'], data['error_count']

        self.config.set("last_extension", opts['extension'])
        self.config.set("default_source_folder", opts['source_folder'])
        self.config.set("default_destination_folder", opts['dest_folder'])
        self.config.set("preserve_structure", opts['preserve_structure'])
        self.config.set("folder_structure", opts['folder_structure'])
        self.config.set("number_duplicates", opts['number_duplicates'])
        self.config.set("recursive_search", opts['recursive_search'])
        self.config.set("enable_size_filter", self.size_check.isChecked())
        self.config.set("min_size", self.min_size_edit.text())
        self.config.set("max_size", self.max_size_edit.text())
        self.config.set("size_unit", self.unit_combo.currentText())
        self.config.set("enable_date_filter", self.date_check.isChecked())
        self.config.set("days_old", self.days_edit.text())
        self.config.save()

        self.copied_label.setText(str(copied))
        self.skipped_label.setText(str(skipped))
        self.progress_label.setText(f"Complete! Copied: {copied}  Skipped: {skipped}")

        summary = f"Total Copied: {copied}\nTotal Skipped: {skipped}"
        if errors == 0 and copied > 0:
            QMessageBox.information(self, "Complete", summary)
        elif copied > 0:
            QMessageBox.warning(self, "Completed with errors", f"{summary}\nErrors: {errors}\n\nCheck status for details.")
        elif errors == 0:
            QMessageBox.information(self, "No Files", "No files were found to process")

    def _on_copy_cancelled(self):
        self._is_copying = False
        self.copy_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Cancelled")
        self._add_status("Operation cancelled by user")
        QMessageBox.information(self, "Cancelled", "Copy operation was cancelled")

    def _on_copy_error(self, data: dict):
        self._is_copying = False
        self.copy_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Error")
        msg = data['message']
        if data['type'] == 'validation':
            QMessageBox.critical(self, "Validation Error", msg)
        elif data['type'] == 'filesystem':
            QMessageBox.critical(self, "File System Error", msg)
        else:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{msg}")

    def _cancel_copy(self):
        if self._is_copying:
            self._cancel_requested = True
            self.cancel_btn.setEnabled(False)
            self.progress_label.setText("Cancelling...")
            self._add_status("Cancellation requested, please wait...")
