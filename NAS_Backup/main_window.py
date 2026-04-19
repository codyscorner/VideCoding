from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import ConfigManager
from models import BackupRecord
from version import VERSION
from worker import BackupWorker


class MainWindow(QMainWindow):
    """NAS Backup — main application window.

    Layout (top → bottom)
    ─────────────────────
      Snapshot Sources list  [QListWidget]  [Add] [Remove]
      Destination row        [label] [path] [Browse]
      Archive row            [label] [path] [Browse]
      Settings row           Retention: [spinbox] days   Threads: [spinbox]
      QProgressBar
      "Status Log" label
      QPlainTextEdit         read-only, auto-scroll, monospace
      Button row             [▶ Start Backup]  [■ Cancel]  … [⬇ Export Log]
    """

    def __init__(self, config: ConfigManager) -> None:
        super().__init__()
        self._config  = config
        self._worker:  Optional[BackupWorker]  = None
        self._records: list[BackupRecord]      = []

        self.setWindowTitle(f"NAS Backup v{VERSION}")
        self.setMinimumSize(780, 660)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "app_icon.ico")))

        self._build_ui()
        self._apply_style()
        self._load_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Snapshot sources ──────────────────────────────────────────
        src_label = QLabel("Snapshot Sources:")
        layout.addWidget(src_label)

        self._source_list = QListWidget()
        self._source_list.setFixedHeight(120)
        self._source_list.setFont(QFont("Consolas", 9))
        layout.addWidget(self._source_list)

        src_btn_row = QHBoxLayout()
        self._btn_add_src = QPushButton("+ Add Folder")
        self._btn_add_src.setFixedHeight(28)
        self._btn_add_src.clicked.connect(self._add_source)

        self._btn_remove_src = QPushButton("− Remove Selected")
        self._btn_remove_src.setFixedHeight(28)
        self._btn_remove_src.clicked.connect(self._remove_source)

        src_btn_row.addWidget(self._btn_add_src)
        src_btn_row.addWidget(self._btn_remove_src)
        src_btn_row.addStretch()
        layout.addLayout(src_btn_row)

        # ── Destination ───────────────────────────────────────────────
        layout.addLayout(self._make_path_row("Destination:", "dest"))

        # ── Settings row ──────────────────────────────────────────────
        settings_row = QHBoxLayout()

        retention_label = QLabel("Retention:")
        retention_label.setFixedWidth(70)
        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(0, 3650)
        self._retention_spin.setValue(365)
        self._retention_spin.setSuffix(" days")
        self._retention_spin.setFixedWidth(100)
        self._retention_spin.setToolTip(
            "Number of days to keep archive snapshots. Set to 0 to disable cleanup."
        )
        self._retention_spin.valueChanged.connect(self._save_config)

        threads_label = QLabel("Threads:")
        threads_label.setFixedWidth(60)
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(1, 128)
        self._threads_spin.setValue(16)
        self._threads_spin.setFixedWidth(70)
        self._threads_spin.valueChanged.connect(self._save_config)

        self._versioned_chk = QCheckBox("Version changed files")
        self._versioned_chk.setToolTip(
            "If a file already exists at the destination with a different size or date,\n"
            "the old copy is renamed (e.g. photo_v2026-04-11_143022.jpg) before the\n"
            "new version is written. Source files are never deleted."
        )
        self._versioned_chk.stateChanged.connect(self._save_config)

        settings_row.addWidget(retention_label)
        settings_row.addWidget(self._retention_spin)
        settings_row.addSpacing(20)
        settings_row.addWidget(threads_label)
        settings_row.addWidget(self._threads_spin)
        settings_row.addSpacing(20)
        settings_row.addWidget(self._versioned_chk)
        settings_row.addStretch()
        layout.addLayout(settings_row)

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

        # ── Control buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_start = QPushButton("▶  Start Backup")
        self._btn_start.setFixedHeight(34)
        self._btn_start.setDefault(True)
        self._btn_start.clicked.connect(self._start_backup)

        self._btn_cancel = QPushButton("■  Cancel")
        self._btn_cancel.setFixedHeight(34)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_backup)

        self._btn_export = QPushButton("⬇  Export Log (CSV)")
        self._btn_export.setFixedHeight(34)
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_log)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_export)

        layout.addLayout(btn_row)

    def _make_path_row(self, label_text: str, attr_prefix: str) -> QHBoxLayout:
        row = QHBoxLayout()

        label = QLabel(label_text)
        label.setFixedWidth(90)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Click Browse to select a folder…")
        line_edit.textChanged.connect(self._save_config)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(lambda: self._browse(line_edit))

        setattr(self, f"_{attr_prefix}_input",  line_edit)
        setattr(self, f"_{attr_prefix}_browse", browse_btn)

        row.addWidget(label)
        row.addWidget(line_edit)
        row.addWidget(browse_btn)
        return row

    def _apply_style(self) -> None:
        """Dark navy/teal theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #0e1a2b;
                color: #d0e8f0;
            }
            QLabel {
                color: #d0e8f0;
            }
            QLineEdit {
                background: #152438;
                color: #d0e8f0;
                border: 1px solid #1e5a7a;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QListWidget {
                background: #0a1520;
                color: #d0e8f0;
                border: 1px solid #1e5a7a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #1e5a7a;
                color: #ffffff;
            }
            QSpinBox {
                background: #152438;
                color: #d0e8f0;
                border: 1px solid #1e5a7a;
                border-radius: 4px;
                padding: 2px 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #1e5a7a;
                border-radius: 2px;
            }
            QProgressBar {
                border: 1px solid #1e5a7a;
                border-radius: 4px;
                background: #152438;
                color: #d0e8f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a7a9a, stop:1 #0d5c7a
                );
                border-radius: 3px;
            }
            QPushButton {
                padding: 4px 14px;
                border: 1px solid #1e5a7a;
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a3a55, stop:1 #0e1a2b
                );
                color: #d0e8f0;
            }
            QPushButton:hover   { background: #1e5a7a; border-color: #2a8aaa; }
            QPushButton:pressed { background: #0d5c7a; }
            QPushButton:disabled { color: #3a5a6a; border-color: #1a3a4a; }
            QPlainTextEdit {
                background: #070f1a;
                color: #a0d8e8;
                border: 1px solid #1e5a7a;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background: #0e1a2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #1e5a7a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
        """)

    # ------------------------------------------------------------------
    # Config load / save
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        for src in self._config.get("snapshot_sources", []):
            self._source_list.addItem(src)
        self._dest_input.setText(self._config.get("destination", ""))
        self._retention_spin.setValue(self._config.get("retention_days", 365))
        self._threads_spin.setValue(self._config.get("robocopy_threads", 16))
        self._versioned_chk.setChecked(self._config.get("versioned_files", True))

    def _save_config(self) -> None:
        sources = [
            self._source_list.item(i).text()
            for i in range(self._source_list.count())
        ]
        self._config.update({
            "snapshot_sources":  sources,
            "destination":       self._dest_input.text().strip(),
            "retention_days":    self._retention_spin.value(),
            "robocopy_threads":  self._threads_spin.value(),
            "versioned_files":   self._versioned_chk.isChecked(),
        })
        self._config.save()

    # ------------------------------------------------------------------
    # Source list management
    # ------------------------------------------------------------------

    def _add_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if not folder:
            return
        # Avoid duplicates
        existing = [
            self._source_list.item(i).text()
            for i in range(self._source_list.count())
        ]
        if folder in existing:
            QMessageBox.information(self, "Already Added", "That folder is already in the list.")
            return
        self._source_list.addItem(folder)
        self._save_config()

    def _remove_source(self) -> None:
        selected = self._source_list.selectedItems()
        if not selected:
            return
        for item in selected:
            self._source_list.takeItem(self._source_list.row(item))
        self._save_config()

    # ------------------------------------------------------------------
    # Browse handler
    # ------------------------------------------------------------------

    def _browse(self, target: QLineEdit) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            target.setText(folder)

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def _start_backup(self) -> None:
        sources = [
            self._source_list.item(i).text()
            for i in range(self._source_list.count())
        ]
        dest = self._dest_input.text().strip()

        if not sources:
            QMessageBox.warning(self, "No Sources", "Add at least one source folder.")
            return
        if not dest:
            QMessageBox.warning(self, "No Destination", "Please set a destination folder.")
            return

        self._records.clear()
        self._log.clear()
        self._progress.setValue(0)
        self._btn_export.setEnabled(False)
        self._set_controls_busy(True)

        log_dir = Path(__file__).parent / "Logs"
        log_dir.mkdir(exist_ok=True)

        self._worker = BackupWorker(
            sources=sources,
            destination=dest,
            retention_days=self._retention_spin.value(),
            threads=self._threads_spin.value(),
            log_dir=log_dir,
            versioned_files=self._versioned_chk.isChecked(),
        )
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress_signal.connect(self._progress.setValue)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _cancel_backup(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._btn_cancel.setEnabled(False)
            self._btn_cancel.setText("Cancelling…")

    def _set_controls_busy(self, busy: bool) -> None:
        self._btn_start.setEnabled(not busy)
        self._btn_cancel.setEnabled(busy)
        self._btn_cancel.setText("■  Cancel")
        self._btn_add_src.setEnabled(not busy)
        self._btn_remove_src.setEnabled(not busy)
        self._dest_browse.setEnabled(not busy)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_log(self, text: str) -> None:
        self._log.appendPlainText(text)
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, records: list) -> None:
        self._records = records
        self._set_controls_busy(False)
        if records:
            self._btn_export.setEnabled(True)

    def _on_error(self, message: str) -> None:
        self._on_log(f"\n[CRITICAL] {message}")
        QMessageBox.critical(self, "Backup Error", message)
        self._set_controls_busy(False)

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup Log",
            f"backup_log_{datetime.now().strftime('%m%d%Y_%H%M')}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh, quoting=csv.QUOTE_ALL)
                writer.writerow(BackupRecord.csv_headers())
                for record in self._records:
                    writer.writerow(record.to_csv_row())
            self._on_log(f"\nLog exported → {path}")
            QMessageBox.information(self, "Export Complete", f"Log saved to:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Close guard
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._worker and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Backup In Progress",
                "A backup is still running.\nCancel it and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._worker.cancel()
                self._worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
