"""Main window UI for Image People Sorter"""

import os
import atexit
import threading
import queue
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QCheckBox, QRadioButton, QButtonGroup, QProgressBar, QPlainTextEdit,
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QSlider,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from config import ConfigManager
from face_detector import ImagePeopleSorter
from ui.styles import STYLESHEET, COLORS
from ui.review_dialog import ReviewDialog


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
        self._review_event = threading.Event()
        self._review_overrides = {}

        self.setWindowTitle(f"Image People Sorter v{self.version}")
        self.setMinimumSize(750, 580)
        self.setStyleSheet(STYLESHEET)
        self.resize(900, 700)

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

        header = QLabel("Image People Sorter")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Sort images by detecting faces — separates people from non-people images")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Source folder
        src_group = QGroupBox("Source Folder")
        src_layout = QVBoxLayout(src_group)
        src_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        src_browse = QPushButton("Browse...")
        src_browse.setMinimumWidth(100)
        src_browse.clicked.connect(self._browse_source)
        src_row.addWidget(self.source_edit, stretch=1)
        src_row.addWidget(src_browse)
        src_layout.addLayout(src_row)
        layout.addWidget(src_group)

        # Destination folder
        dst_group = QGroupBox("Destination Folder")
        dst_layout = QVBoxLayout(dst_group)
        dst_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        dst_browse = QPushButton("Browse...")
        dst_browse.setMinimumWidth(100)
        dst_browse.clicked.connect(self._browse_dest)
        dst_row.addWidget(self.dest_edit, stretch=1)
        dst_row.addWidget(dst_browse)
        dst_layout.addLayout(dst_row)
        info = QLabel("Images will be sorted into 'People', 'Unsure', and 'No_People' subfolders")
        info.setObjectName("subtitle")
        dst_layout.addWidget(info)
        layout.addWidget(dst_group)

        # Options
        opt_group = QGroupBox("Options")
        opt_vlayout = QVBoxLayout(opt_group)
        opt_layout = QHBoxLayout()
        self.recursive_check = QCheckBox("Search subfolders recursively")
        self.recursive_check.setChecked(True)
        opt_layout.addWidget(self.recursive_check)
        opt_layout.addSpacing(30)
        opt_layout.addWidget(QLabel("File Operation:"))
        self.copy_radio = QRadioButton("Copy")
        self.copy_radio.setChecked(True)
        self.move_radio = QRadioButton("Move")
        self._file_op_group = QButtonGroup()
        self._file_op_group.addButton(self.copy_radio)
        self._file_op_group.addButton(self.move_radio)
        opt_layout.addWidget(self.copy_radio)
        opt_layout.addWidget(self.move_radio)
        opt_layout.addStretch()
        opt_vlayout.addLayout(opt_layout)

        opt_layout2 = QHBoxLayout()
        self.review_check = QCheckBox("Review results before saving (veto false positives)")
        opt_layout2.addWidget(self.review_check)
        opt_layout2.addSpacing(30)
        self.csv_check = QCheckBox("Save CSV report of decisions")
        self.csv_check.setChecked(True)
        opt_layout2.addWidget(self.csv_check)
        opt_layout2.addStretch()
        opt_vlayout.addLayout(opt_layout2)

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold:"))
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(5, 95)
        self.confidence_slider.setValue(30)
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)
        conf_layout.addWidget(self.confidence_slider, stretch=1)
        self.confidence_value_label = QLabel("30%")
        self.confidence_value_label.setMinimumWidth(40)
        conf_layout.addWidget(self.confidence_value_label)
        opt_vlayout.addLayout(conf_layout)
        conf_hint = QLabel(
            "Lower = more sensitive to distant/unclear people (more false positives). "
            "Borderline detections land in an Unsure folder instead of People."
        )
        conf_hint.setObjectName("subtitle")
        conf_hint.setWordWrap(True)
        opt_vlayout.addWidget(conf_hint)

        layout.addWidget(opt_group)

        # Buttons
        btn_row = QHBoxLayout()
        self.sort_btn = QPushButton("Sort Images")
        self.sort_btn.clicked.connect(self._start_sort)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_sort)
        btn_row.addWidget(self.sort_btn)
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
        self.status_log = QPlainTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMaximumBlockCount(5000)  # auto-trims oldest lines
        status_layout.addWidget(self.status_log)
        layout.addWidget(status_group, stretch=1)

    def _browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def _browse_dest(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)

    def _load_config(self):
        self.source_edit.setText(self.config.get("default_source_folder", ""))
        self.dest_edit.setText(self.config.get("default_destination_folder", ""))
        self.recursive_check.setChecked(self.config.get("recursive_search", True))
        copy_mode = self.config.get("copy_mode", True)
        self.copy_radio.setChecked(copy_mode)
        self.move_radio.setChecked(not copy_mode)
        self.confidence_slider.setValue(self.config.get("confidence_threshold", 30))
        self.review_check.setChecked(self.config.get("review_mode", False))
        self.csv_check.setChecked(self.config.get("write_csv_report", True))

    def _save_config(self):
        self.config.set("default_source_folder", self.source_edit.text())
        self.config.set("default_destination_folder", self.dest_edit.text())
        self.config.set("recursive_search", self.recursive_check.isChecked())
        self.config.set("copy_mode", self.copy_radio.isChecked())
        self.config.set("confidence_threshold", self.confidence_slider.value())
        self.config.set("review_mode", self.review_check.isChecked())
        self.config.set("write_csv_report", self.csv_check.isChecked())
        self.config.save()

    def _on_confidence_changed(self, value: int):
        self.confidence_value_label.setText(f"{value}%")

    def _start_sort(self):
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        if not source:
            QMessageBox.critical(self, "Error", "Please select a source folder")
            return
        if not dest:
            QMessageBox.critical(self, "Error", "Please select a destination folder")
            return
        if source == dest:
            QMessageBox.critical(self, "Error", "Source and destination folders cannot be the same")
            return
        if not os.path.exists(source):
            QMessageBox.critical(self, "Error", "Source folder does not exist")
            return

        self._save_config()
        self._is_processing = True
        self._cancel_requested = False
        self.sort_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_log.clear()

        options = {
            'source': source,
            'dest': dest,
            'recursive': self.recursive_check.isChecked(),
            'copy_mode': self.copy_radio.isChecked(),
            'confidence_threshold': self.confidence_slider.value() / 100.0,
            'review_mode': self.review_check.isChecked(),
            'write_csv_report': self.csv_check.isChecked(),
        }

        thread = threading.Thread(target=self._sort_worker, args=(options,), daemon=True)
        thread.start()
        self._poll_timer.start()

    def _sort_worker(self, options: dict):
        try:
            self._message_queue.put(('status', "Starting sort operation..."))
            review_callback = self._request_review if options['review_mode'] else None
            sorter = ImagePeopleSorter(
                status_callback=lambda msg: self._message_queue.put(('status', msg)),
                progress_callback=lambda cur, tot, fname, fp: self._message_queue.put(
                    ('progress', {'current': cur, 'total': tot, 'filename': fname})
                ),
                cancel_check=lambda: self._cancel_requested,
                copy_mode=options['copy_mode'],
                confidence_threshold=options['confidence_threshold'],
                review_callback=review_callback,
                write_csv_report=options['write_csv_report'],
            )
            results, people_count, no_people_count, unsure_count = sorter.sort_images(
                options['source'], options['dest'], options['recursive']
            )
            if self._cancel_requested:
                self._message_queue.put(('cancelled', None))
            else:
                error_count = sum(1 for r in results if not r.success)
                self._message_queue.put(('complete', {
                    'people_count': people_count,
                    'no_people_count': no_people_count,
                    'unsure_count': unsure_count,
                    'error_count': error_count,
                    'copy_mode': options['copy_mode'],
                }))
        except ValueError as e:
            self._message_queue.put(('error', {'type': 'validation', 'message': str(e)}))
        except Exception as e:
            self._message_queue.put(('error', {'type': 'unexpected', 'message': str(e)}))

    def _request_review(self, entries: list) -> dict:
        """Called on the background sort thread. Queues a review request for
        the main thread and blocks until the modal dialog is closed."""
        self._review_event.clear()
        self._review_overrides = {}
        self._message_queue.put(('review_request', entries))
        self._review_event.wait()
        return self._review_overrides

    def _process_messages(self):
        status_lines = []
        terminal_event = None

        # Drain up to 200 messages per tick — avoids blocking the UI thread
        # while still catching up on backlog quickly at 14k-image scale
        try:
            for _ in range(200):
                msg_type, data = self._message_queue.get_nowait()

                if msg_type == 'status':
                    status_lines.append(data)

                elif msg_type == 'progress':
                    self.progress_bar.setValue(data['current'])
                    self.progress_label.setText(f"{data['current']}%: {data['filename']}")

                elif msg_type == 'review_request':
                    # Flush pending status lines before the modal dialog blocks the UI
                    if status_lines:
                        self.status_log.appendPlainText('\n'.join(status_lines))
                        status_lines = []
                    self._show_review_dialog(data)

                elif msg_type in ('complete', 'cancelled', 'error'):
                    terminal_event = (msg_type, data)
                    break

        except queue.Empty:
            pass

        # Batch-append all status lines in one Qt call — scrollToBottom once
        if status_lines:
            self.status_log.appendPlainText('\n'.join(status_lines))

        if terminal_event:
            msg_type, data = terminal_event
            self._poll_timer.stop()
            if msg_type == 'complete':
                self._on_complete(data)
            elif msg_type == 'cancelled':
                self._on_cancelled()
            elif msg_type == 'error':
                self._on_error(data)

    def _show_review_dialog(self, entries: list):
        """Runs on the main thread (called from the poll timer). Blocks
        modally while the background sort thread waits on _review_event."""
        try:
            dialog = ReviewDialog(entries, parent=self)
            dialog.exec()
            self._review_overrides = dialog.get_overrides()
        except Exception:
            self._review_overrides = {}
        finally:
            self._review_event.set()

    def _on_complete(self, data: dict):
        self._is_processing = False
        self.sort_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Complete!")
        action = "copied" if data['copy_mode'] else "moved"
        summary = (
            f"People: {data['people_count']} images {action}\n"
            f"Unsure: {data['unsure_count']} images {action}\n"
            f"No People: {data['no_people_count']} images {action}"
        )
        if data['error_count'] == 0:
            QMessageBox.information(
                self, "Success",
                f"Successfully sorted images!\n\n{summary}"
            )
        else:
            QMessageBox.warning(
                self, "Completed with errors",
                f"Sorted images with {data['error_count']} errors.\n\n{summary}\n\n"
                f"Check status log for details."
            )

    def _on_cancelled(self):
        self._is_processing = False
        self.sort_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Cancelled")
        self.status_log.appendPlainText("Operation cancelled by user")

    def _on_error(self, data: dict):
        self._is_processing = False
        self.sort_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Error")
        if data['type'] == 'validation':
            QMessageBox.critical(self, "Validation Error", data['message'])
        else:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{data['message']}")

    def _cancel_sort(self):
        if self._is_processing:
            self._cancel_requested = True
            self.cancel_btn.setEnabled(False)
            self.progress_label.setText("Cancelling...")
            self.status_log.appendPlainText("Cancellation requested, killing workers...")
            self._kill_child_processes()

    def _kill_child_processes(self):
        try:
            import psutil
            current = psutil.Process(os.getpid())
            children = current.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
            psutil.wait_procs(children, timeout=1)
            for child in current.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
        except Exception:
            pass

    def closeEvent(self, event):
        if self._is_processing:
            self._cancel_requested = True
        self._poll_timer.stop()
        self._kill_child_processes()
        self._save_config()
        event.accept()
