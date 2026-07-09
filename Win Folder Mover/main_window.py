# main_window.py — MainWindow(QMainWindow)
#
# Pure GUI class.  It knows nothing about how files are moved; it only
# starts the worker, wires up its signals, and reacts to them.
#
# pip install PyQt6

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models import FileRecord
from version import VERSION
from worker import MoveWorker


class MainWindow(QMainWindow):
    """Top-level application window.

    Layout (top → bottom)
    ─────────────────────
      Source folder row   [label] [read-only QLineEdit] [Browse]
      Dest folder row     [label] [read-only QLineEdit] [Browse]
      ── separator ──
      QProgressBar        0 – 100 %
      "Status Log" label
      QPlainTextEdit      read-only, auto-scroll, monospace
      Button row          [Start Move] [Cancel/Stop]  … [Export Logs]
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Windows Folder Mover v{VERSION}")
        self.setMinimumSize(720, 560)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "app_icon.ico")))

        self._worker:  Optional[MoveWorker]  = None
        self._records: list[FileRecord]      = []

        # Multi-folder queue state
        self._jobs: list[tuple[str, str]] = []
        self._job_index: int = 0
        self._queue_cancelled: bool = False

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Path selectors ────────────────────────────────────────────
        layout.addLayout(self._make_path_row("Source Folder:", "source"))
        layout.addLayout(self._make_path_row("Destination Folder:", "dest"))

        # ── Multi-folder queue ────────────────────────────────────────
        queue_row = QHBoxLayout()
        self._btn_add_queue = QPushButton("＋  Add to Queue")
        self._btn_add_queue.clicked.connect(self._add_to_queue)
        self._btn_remove_queue = QPushButton("－  Remove Selected")
        self._btn_remove_queue.clicked.connect(self._remove_from_queue)
        queue_row.addWidget(self._btn_add_queue)
        queue_row.addWidget(self._btn_remove_queue)
        queue_row.addStretch()
        layout.addLayout(queue_row)

        self._queue_list = QListWidget()
        self._queue_list.setMaximumHeight(80)
        layout.addWidget(self._queue_list)

        # ── Progress bar ──────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(22)
        layout.addWidget(self._progress)

        # ── Status log ────────────────────────────────────────────────
        log_label = QLabel("Status Log:")
        layout.addWidget(log_label)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 9))
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._log)

        # ── Dry-run / verify toggles ───────────────────────────────────
        self._dry_run_check = QCheckBox("Dry Run  (preview only — no files will be moved)")
        self._dry_run_check.stateChanged.connect(self._on_dry_run_toggle)
        layout.addWidget(self._dry_run_check)

        self._verify_check = QCheckBox(
            "Verify after move  (size check before deleting source on cross-drive moves)"
        )
        layout.addWidget(self._verify_check)

        # ── Control buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_start = QPushButton("▶  Start Move")
        self._btn_start.setFixedHeight(34)
        self._btn_start.setDefault(True)
        self._btn_start.clicked.connect(self._start_move)

        self._btn_cancel = QPushButton("■  Cancel / Stop")
        self._btn_cancel.setFixedHeight(34)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_move)

        self._btn_export = QPushButton("⬇  Export Logs (CSV)")
        self._btn_export.setFixedHeight(34)
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_logs)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_export)

        layout.addLayout(btn_row)

    def _make_path_row(self, label_text: str, attr_prefix: str) -> QHBoxLayout:
        """Build a labelled path-selector row and store the widgets as
        ``self._<attr_prefix>_input`` and ``self._<attr_prefix>_browse``."""
        row = QHBoxLayout()

        label = QLabel(label_text)
        label.setFixedWidth(140)

        line_edit = QLineEdit()
        line_edit.setReadOnly(True)
        line_edit.setPlaceholderText("Click Browse to select a folder…")

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(90)
        # Capture line_edit in the lambda so each button drives its own field.
        browse_btn.clicked.connect(lambda: self._browse(line_edit))

        setattr(self, f"_{attr_prefix}_input",  line_edit)
        setattr(self, f"_{attr_prefix}_browse", browse_btn)

        row.addWidget(label)
        row.addWidget(line_edit)
        row.addWidget(browse_btn)
        return row

    def _apply_style(self) -> None:
        """Medium red theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #2b1010;
                color: #f0d0d0;
            }
            QLabel {
                color: #f0d0d0;
            }
            QLineEdit {
                background: #3d1a1a;
                color: #f0d0d0;
                border: 1px solid #7a2a2a;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QLineEdit[readOnly="true"] {
                background: #3d1a1a;
                color: #c8a0a0;
            }
            QProgressBar {
                border: 1px solid #7a2a2a;
                border-radius: 4px;
                background: #3d1a1a;
                color: #f0d0d0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #922b21
                );
                border-radius: 3px;
            }
            QPushButton {
                padding: 4px 14px;
                border: 1px solid #7a2a2a;
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a1f1f, stop:1 #3d1414
                );
                color: #f0d0d0;
            }
            QPushButton:hover   { background: #7a2a2a; border-color: #c0392b; }
            QPushButton:pressed { background: #922b21; }
            QPushButton:disabled { color: #6b4040; border-color: #4a2020; }
            QPlainTextEdit {
                background: #1a0a0a;
                color: #f0c0c0;
                border: 1px solid #7a2a2a;
                border-radius: 4px;
            }
            QListWidget {
                background: #1a0a0a;
                color: #f0c0c0;
                border: 1px solid #7a2a2a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #7a2a2a;
                color: #f0d0d0;
            }
            QScrollBar:vertical {
                background: #2b1010;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #7a2a2a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
            QCheckBox {
                color: #f0d0d0;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #7a2a2a;
                border-radius: 3px;
                background: #3d1a1a;
            }
            QCheckBox::indicator:checked {
                background: #c0392b;
                border-color: #c0392b;
            }
        """)

    # ------------------------------------------------------------------
    # Browse handler
    # ------------------------------------------------------------------

    def _on_dry_run_toggle(self) -> None:
        if self._dry_run_check.isChecked():
            self._btn_start.setText("▶  Start Dry Run")
        else:
            self._btn_start.setText("▶  Start Move")

    def _browse(self, target: QLineEdit) -> None:
        current = target.text().strip()
        start_dir = current if current and os.path.exists(current) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        if folder:
            target.setText(folder)

    # ------------------------------------------------------------------
    # Multi-folder queue
    # ------------------------------------------------------------------

    def _add_to_queue(self) -> None:
        source = self._source_input.text().strip()
        dest   = self._dest_input.text().strip()

        if not source or not dest:
            QMessageBox.warning(
                self, "Missing Paths",
                "Select both a source and a destination folder before adding to the queue."
            )
            return
        if source == dest:
            QMessageBox.warning(
                self, "Same Folder",
                "Source and destination folders must be different."
            )
            return

        item = QListWidgetItem(f"{source}   →   {dest}")
        item.setData(Qt.ItemDataRole.UserRole, (source, dest))
        self._queue_list.addItem(item)
        self._source_input.clear()
        self._dest_input.clear()

    def _remove_from_queue(self) -> None:
        row = self._queue_list.currentRow()
        if row >= 0:
            self._queue_list.takeItem(row)

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def _start_move(self) -> None:
        jobs: list[tuple[str, str]] = [
            self._queue_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._queue_list.count())
        ]

        if not jobs:
            source = self._source_input.text().strip()
            dest   = self._dest_input.text().strip()

            if not source or not dest:
                QMessageBox.warning(
                    self, "Missing Paths",
                    "Please select both a source and a destination folder."
                )
                return
            if source == dest:
                QMessageBox.warning(
                    self, "Same Folder",
                    "Source and destination folders must be different."
                )
                return
            jobs = [(source, dest)]

        # ── Reset UI state ────────────────────────────────────────────
        self._jobs = jobs
        self._job_index = 0
        self._queue_cancelled = False
        self._records = []
        self._log.clear()
        self._progress.setValue(0)
        self._btn_export.setEnabled(False)
        self._set_controls_busy(True)
        self._queue_list.clear()

        self._run_next_job()

    def _run_next_job(self) -> None:
        source, dest = self._jobs[self._job_index]
        if len(self._jobs) > 1:
            self._on_log(
                f"\n════  Job {self._job_index + 1}/{len(self._jobs)}: "
                f"{source}  →  {dest}  ════"
            )

        dry_run = self._dry_run_check.isChecked()
        verify  = self._verify_check.isChecked()
        self._worker = MoveWorker(source, dest, dry_run=dry_run, verify=verify)
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress_signal.connect(self._progress.setValue)
        self._worker.finished_signal.connect(self._on_job_finished)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _cancel_move(self) -> None:
        if self._worker and self._worker.isRunning():
            self._queue_cancelled = True
            self._worker.cancel()
            # Disable the button immediately so the user knows the request
            # was received; the thread will still finish its current file.
            self._btn_cancel.setEnabled(False)
            self._btn_cancel.setText("Cancelling…")

    def _set_controls_busy(self, busy: bool) -> None:
        """Toggle interactive controls based on whether a move is running."""
        self._btn_start.setEnabled(not busy)
        self._btn_cancel.setEnabled(busy)
        self._btn_cancel.setText("■  Cancel / Stop")   # reset label
        self._source_browse.setEnabled(not busy)
        self._dest_browse.setEnabled(not busy)
        self._btn_add_queue.setEnabled(not busy)
        self._btn_remove_queue.setEnabled(not busy)

    # ------------------------------------------------------------------
    # Signal handlers  (all called on the GUI / main thread by Qt)
    # ------------------------------------------------------------------

    def _on_log(self, text: str) -> None:
        """Append *text* to the log pane and auto-scroll to the bottom."""
        self._log.appendPlainText(text)
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_job_finished(self, records: list) -> None:
        """Called when one queued job's worker thread completes."""
        self._records.extend(records)
        self._job_index += 1

        if not self._queue_cancelled and self._job_index < len(self._jobs):
            self._run_next_job()
            return

        self._set_controls_busy(False)
        if self._records and not self._dry_run_check.isChecked():
            self._btn_export.setEnabled(True)

    def _on_error(self, message: str) -> None:
        """Called for an unrecoverable exception inside the worker."""
        self._on_log(f"\n[CRITICAL] {message}")
        QMessageBox.critical(self, "Worker Error", message)
        self._set_controls_busy(False)

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def _export_logs(self) -> None:
        """Prompt the user for a save path and write all FileRecords to CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Move Log",
            f"move_log_{datetime.now().strftime('%m%d%Y_%H%M')}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                # utf-8-sig adds a BOM so Excel auto-detects UTF-8 encoding.
                writer = csv.writer(fh, quoting=csv.QUOTE_ALL)
                writer.writerow(FileRecord.csv_headers())
                for record in self._records:
                    writer.writerow(record.to_csv_row())

            self._on_log(f"\nLog exported → {path}")
            QMessageBox.information(
                self, "Export Complete", f"Log saved to:\n{path}"
            )

        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Window close guard
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Prevent closing while a move is in progress."""
        if self._worker and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Move In Progress",
                "A move operation is still running.\n"
                "Cancel it and close the window?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._worker.cancel()
                self._worker.wait()          # block until the thread exits
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
