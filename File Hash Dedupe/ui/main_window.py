"""Main window UI for File Hash Dedupe"""

import os
import atexit
import threading
import queue
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QCheckBox, QSpinBox, QProgressBar, QListWidget,
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from config import ConfigManager
from hasher import FileDeduplicator
from ui.styles import STYLESHEET, COLORS


def _cleanup_all_children():
    try:
        import psutil
        current = psutil.Process(os.getpid())
        for child in current.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
    except Exception:
        pass

atexit.register(_cleanup_all_children)


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version

        self._is_processing = False
        self._cancel_requested = False
        self._message_queue = queue.Queue()

        self.setWindowTitle(f"File Hash Dedupe v{self.version}")
        self.setMinimumSize(700, 550)
        self.setStyleSheet(STYLESHEET)

        geom = self.config.window_geometry
        if geom:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(geom.encode()))
            except Exception:
                self.resize(750, 600)
        else:
            self.resize(750, 600)

        self._build_ui()
        self._load_config()

        self._poll_timer = QTimer()
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._process_messages)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QLabel("File Hash Dedupe")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Find and move duplicate files based on content hash")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Source folder
        src_group = QGroupBox("Source Folder")
        src_layout = QVBoxLayout(src_group)
        src_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.setMinimumWidth(100)
        browse_btn.clicked.connect(self._browse_source)
        src_row.addWidget(self.source_edit, stretch=1)
        src_row.addWidget(browse_btn)
        src_layout.addLayout(src_row)
        self.source_info_label = QLabel("Duplicates will be moved to a 'Dupes' subfolder in the source folder")
        self.source_info_label.setObjectName("subtitle")
        src_layout.addWidget(self.source_info_label)
        layout.addWidget(src_group)

        # Options
        opt_group = QGroupBox("Options")
        opt_layout = QVBoxLayout(opt_group)
        self.recursive_check = QCheckBox("Search subfolders recursively")
        self.recursive_check.setChecked(True)
        opt_layout.addWidget(self.recursive_check)

        self.permanent_delete_check = QCheckBox("⚠  Permanently delete duplicates (no Dupes folder)")
        self.permanent_delete_check.setChecked(False)
        self.permanent_delete_check.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        self.permanent_delete_check.toggled.connect(self._on_permanent_delete_toggled)
        opt_layout.addWidget(self.permanent_delete_check)

        cpu_count = os.cpu_count() or 4
        workers_row = QHBoxLayout()
        workers_row.addWidget(QLabel("Hashing workers:"))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, cpu_count)
        self.workers_spin.setValue(max(2, min(16, cpu_count // 2)))
        self.workers_spin.setFixedWidth(60)
        workers_row.addWidget(self.workers_spin)
        cpu_lbl = QLabel(f"(1 – {cpu_count} logical CPUs on this machine)")
        cpu_lbl.setObjectName("subtitle")
        workers_row.addWidget(cpu_lbl)
        workers_row.addStretch()
        opt_layout.addLayout(workers_row)
        layout.addWidget(opt_group)

        # Buttons
        btn_row = QHBoxLayout()
        self.dedupe_btn = QPushButton("Find Duplicates")
        self.dedupe_btn.clicked.connect(self._start_dedupe)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_dedupe)
        btn_row.addWidget(self.dedupe_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("subtitle")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Status log
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.status_list = QListWidget()
        status_layout.addWidget(self.status_list)
        layout.addWidget(status_group, stretch=1)

    def _on_permanent_delete_toggled(self, checked: bool):
        if checked:
            self.source_info_label.setText("⚠  Duplicates will be permanently deleted — cannot be undone")
        else:
            self.source_info_label.setText("Duplicates will be moved to a 'Dupes' subfolder in the source folder")

    def _browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def _load_config(self):
        if self.config.source_folder:
            self.source_edit.setText(self.config.source_folder)
        self.recursive_check.setChecked(self.config.recursive)
        self.workers_spin.setValue(self.config.get('io_workers', self.workers_spin.value()))

    def _save_config(self):
        self.config.source_folder = self.source_edit.text()
        self.config.recursive = self.recursive_check.isChecked()
        self.config.window_geometry = self.saveGeometry().toHex().data().decode()
        self.config.set('io_workers', self.workers_spin.value())
        self.config.save()

    def _start_dedupe(self):
        source = self.source_edit.text().strip()
        if not source:
            QMessageBox.critical(self, "Validation Error", "Please select a source folder")
            return
        if not os.path.exists(source):
            QMessageBox.critical(self, "Validation Error", "Source folder does not exist")
            return

        permanent_delete = self.permanent_delete_check.isChecked()

        if permanent_delete:
            reply = QMessageBox.warning(
                self, "Permanent Delete",
                "Duplicates will be permanently deleted and cannot be recovered.\n\nAre you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._save_config()
        self._is_processing = True
        self._cancel_requested = False
        self.dedupe_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_list.clear()

        thread = threading.Thread(
            target=self._dedupe_worker,
            args=(source, self.recursive_check.isChecked(), self.workers_spin.value(), permanent_delete),
            daemon=True
        )
        thread.start()
        self._poll_timer.start()

    def _dedupe_worker(self, source: str, recursive: bool, io_workers: int, permanent_delete: bool = False):
        try:
            deduplicator = FileDeduplicator(
                status_callback=lambda msg: self._message_queue.put(('status', msg)),
                progress_callback=lambda cur, total, fname: self._message_queue.put(
                    ('progress', {'current': cur, 'total': total, 'filename': fname})
                ),
                cancel_check=lambda: self._cancel_requested,
                max_workers=io_workers
            )
            results, total, unique, moved = deduplicator.find_and_move_duplicates(
                source, recursive=recursive, permanent_delete=permanent_delete
            )
            if self._cancel_requested:
                self._message_queue.put(('cancelled', None))
            else:
                self._message_queue.put(('complete', {
                    'total': total, 'unique': unique, 'moved': moved,
                    'permanent_delete': permanent_delete
                }))
        except Exception as e:
            self._message_queue.put(('error', {'type': 'unexpected', 'message': str(e)}))

    def _process_messages(self):
        try:
            for _ in range(50):  # max messages per tick — keeps UI responsive
                msg_type, data = self._message_queue.get_nowait()

                if msg_type == 'status':
                    self.status_list.addItem(data)
                    self.status_list.scrollToBottom()

                elif msg_type == 'progress':
                    self.progress_bar.setValue(data['current'])
                    self.progress_label.setText(f"{data['current']}%: {data['filename']}")

                elif msg_type == 'complete':
                    self._poll_timer.stop()
                    self._on_complete(data)
                    return

                elif msg_type == 'cancelled':
                    self._poll_timer.stop()
                    self._on_cancelled()
                    return

                elif msg_type == 'error':
                    self._poll_timer.stop()
                    self._on_error(data)
                    return

        except queue.Empty:
            pass

    def _on_complete(self, data: dict):
        self._is_processing = False
        self.dedupe_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Complete!")
        action_word = "deleted" if data.get('permanent_delete') else "moved to Dupes"
        QMessageBox.information(
            self, "Success",
            f"Deduplication complete!\n\n"
            f"Total files scanned: {data['total']}\n"
            f"Unique files: {data['unique']}\n"
            f"Duplicates {action_word}: {data['moved']}"
        )

    def _on_cancelled(self):
        self._is_processing = False
        self.dedupe_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Cancelled")
        self.status_list.addItem("Operation cancelled by user")
        self.status_list.scrollToBottom()

    def _on_error(self, data: dict):
        self._is_processing = False
        self.dedupe_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Error")
        msg = data['message']
        if data['type'] == 'validation':
            QMessageBox.critical(self, "Validation Error", msg)
        else:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{msg}")

    def _cancel_dedupe(self):
        if self._is_processing:
            self._cancel_requested = True
            self.cancel_btn.setEnabled(False)
            self.progress_label.setText("Cancelling...")
            self.status_list.addItem("Cancellation requested...")
            self.status_list.scrollToBottom()

    def closeEvent(self, event):
        if self._is_processing:
            self._cancel_requested = True
        self._save_config()
        event.accept()
