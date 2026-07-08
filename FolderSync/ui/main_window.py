import csv
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from worker import SyncWorker


def _fmt_size(size: int) -> str:
    val = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} TB"


class MainWindow(QMainWindow):
    _PRESETS = {
        "-- Select Preset --": "",
        "All Files":  "*.*",
        "Archives":   "*.zip, *.rar, *.7z, *.tar, *.gz, *.bz2, *.xz, *.iso",
        "Audio":      "*.mp3, *.wav, *.flac, *.aac, *.ogg, *.wma, *.m4a, *.opus, *.aiff",
        "Code":       "*.py, *.js, *.ts, *.html, *.css, *.java, *.cpp, *.c, *.h, *.cs, *.go, *.rs",
        "Data":       "*.json, *.xml, *.csv, *.yaml, *.yml, *.sql, *.db, *.sqlite",
        "Documents":  "*.pdf, *.doc, *.docx, *.xls, *.xlsx, *.ppt, *.pptx, *.txt, *.rtf, *.odt",
        "Images":     "*.jpg, *.jpeg, *.png, *.gif, *.bmp, *.tiff, *.tif, *.webp, *.svg, *.ico, *.raw, *.heic, *.heif",
        "Videos":     "*.mp4, *.avi, *.mkv, *.mov, *.wmv, *.flv, *.webm, *.m4v, *.mpeg, *.mpg, *.3gp, *.ts",
    }

    _NO_PROFILE = "-- No Profile --"
    _WATCH_DEBOUNCE_MS = 1500

    def __init__(self, config, profiles, base_dir: Path, version: str):
        super().__init__()
        self._config = config
        self._profiles = profiles
        self._base_dir = base_dir
        self._version = version
        self._worker: SyncWorker | None = None
        self._diff_files: list = []
        self._last_report: list = []
        self._last_action = ""   # "Copied" or "Deleted", for report labeling

        self._watcher: QFileSystemWatcher | None = None
        self._watch_timer = QTimer(self)
        self._watch_timer.setSingleShot(True)
        self._watch_timer.timeout.connect(self._on_watch_triggered)

        self.setWindowTitle(f"Folder Sync v{version}")
        w, h = self._config.get("window_size", [900, 700])
        self.resize(w, h)

        self._build_ui()
        self._load_saved_paths()
        self._refresh_profile_combo()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 14)

        # Header
        header = QLabel(f"Folder Sync  v{self._version}")
        header.setObjectName("header")
        layout.addWidget(header)

        # Profile row
        prof_row = QHBoxLayout()
        prof_row.addWidget(QLabel("Profile:"))
        self._profile_combo = QComboBox()
        self._profile_combo.setFixedWidth(180)
        self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
        prof_row.addWidget(self._profile_combo)
        self._save_profile_btn = QPushButton("Save As...")
        self._save_profile_btn.setObjectName("browse")
        self._save_profile_btn.clicked.connect(self._on_save_profile)
        prof_row.addWidget(self._save_profile_btn)
        self._delete_profile_btn = QPushButton("Delete")
        self._delete_profile_btn.setObjectName("browse")
        self._delete_profile_btn.clicked.connect(self._on_delete_profile)
        prof_row.addWidget(self._delete_profile_btn)
        prof_row.addStretch()
        prof_widget = QWidget()
        prof_widget.setLayout(prof_row)
        layout.addWidget(prof_widget)

        # Source row
        layout.addWidget(self._path_row("Source:", "_src_edit", "_src_browse"))

        # Destination row
        layout.addWidget(self._path_row("Destination:", "_dst_edit", "_dst_browse"))

        # Options row
        opt_row = QHBoxLayout()
        self._subfolder_check = QCheckBox("Include subfolders")
        self._subfolder_check.setChecked(self._config.get("include_subfolders", False))
        opt_row.addWidget(self._subfolder_check)
        self._hash_check = QCheckBox("Verify by hash")
        self._hash_check.setChecked(self._config.get("hash_verify", False))
        opt_row.addWidget(self._hash_check)
        self._watch_check = QCheckBox("Watch mode (auto-sync on change)")
        self._watch_check.toggled.connect(self._on_watch_toggled)
        opt_row.addWidget(self._watch_check)
        opt_row.addStretch()
        opt_widget = QWidget()
        opt_widget.setLayout(opt_row)
        layout.addWidget(opt_widget)

        # Mode row (forward / reverse)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._forward_radio = QRadioButton("Sync (Source → Destination)")
        self._forward_radio.setChecked(True)
        self._reverse_radio = QRadioButton("Reverse Diff (find extras in Destination)")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._forward_radio)
        self._mode_group.addButton(self._reverse_radio)
        self._forward_radio.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self._forward_radio)
        mode_row.addWidget(self._reverse_radio)
        mode_row.addStretch()
        mode_widget = QWidget()
        mode_widget.setLayout(mode_row)
        layout.addWidget(mode_widget)

        # File mask row
        mask_top = QHBoxLayout()
        mask_top.addWidget(QLabel("File Mask:"))
        mask_top.addSpacing(12)
        mask_top.addWidget(QLabel("Presets:"))
        self._preset_combo = QComboBox()
        self._preset_combo.setFixedWidth(160)
        self._preset_combo.addItems(list(self._PRESETS.keys()))
        self._preset_combo.currentTextChanged.connect(self._on_preset_selected)
        mask_top.addWidget(self._preset_combo)
        mask_top.addStretch()
        mask_top_widget = QWidget()
        mask_top_widget.setLayout(mask_top)
        layout.addWidget(mask_top_widget)

        self._mask_edit = QLineEdit()
        self._mask_edit.setPlaceholderText("e.g.  *.mp4, *.mkv   or leave blank for all files")
        self._mask_edit.setText(self._config.get("file_mask", ""))
        layout.addWidget(self._mask_edit)

        hint = QLabel("Tip: comma-separated wildcards — *.mp4, *.mov   or just mp4, mov")
        hint.setObjectName("status")
        layout.addWidget(hint)

        # Button row
        btn_row = QHBoxLayout()
        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setFixedWidth(100)
        self._compare_btn.clicked.connect(self._on_compare)
        self._sync_btn = QPushButton("Sync")
        self._sync_btn.setFixedWidth(100)
        self._sync_btn.clicked.connect(self._on_sync)
        self._sync_btn.setEnabled(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.setObjectName("cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setVisible(False)
        self._report_btn = QPushButton("Export Report (CSV)")
        self._report_btn.setObjectName("browse")
        self._report_btn.clicked.connect(self._on_export_report)
        self._report_btn.setEnabled(False)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(100)
        self._clear_btn.setObjectName("browse")
        self._clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self._compare_btn)
        btn_row.addWidget(self._sync_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._report_btn)
        btn_row.addWidget(self._clear_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_row)
        layout.addWidget(btn_widget)

        # Status label
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("status")
        layout.addWidget(self._status_label)

        # Table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Name", "Size", "Reason", "Source Path"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 220)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 130)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, stretch=3)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # Log pane
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(140)
        layout.addWidget(self._log, stretch=1)

    def _path_row(self, label: str, edit_attr: str, browse_attr: str) -> QWidget:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(88)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        edit = QLineEdit()
        edit.setPlaceholderText("Select a folder...")
        browse = QPushButton("Browse")
        browse.setObjectName("browse")
        browse.setFixedWidth(82)

        # Store as instance attributes
        setattr(self, edit_attr, edit)
        setattr(self, browse_attr, browse)

        browse.clicked.connect(lambda: self._browse_folder(edit))

        row.addWidget(lbl)
        row.addWidget(edit)
        row.addWidget(browse)
        w = QWidget()
        w.setLayout(row)
        return w

    def _browse_folder(self, edit: QLineEdit) -> None:
        start = edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start)
        if folder:
            edit.setText(folder)

    def _on_preset_selected(self, text: str) -> None:
        value = self._PRESETS.get(text, "")
        if value:
            self._mask_edit.setText(value)

    def _on_mode_changed(self, checked: bool) -> None:
        reverse = not checked
        self._table.setHorizontalHeaderLabels(
            ["Name", "Size", "Reason", "Destination Path" if reverse else "Source Path"]
        )
        self._sync_btn.setText("Delete Extra" if reverse else "Sync")
        self._on_clear()

    def _load_saved_paths(self) -> None:
        self._src_edit.setText(self._config.get("source_path", ""))
        self._dst_edit.setText(self._config.get("dest_path", ""))
        self._mask_edit.setText(self._config.get("file_mask", ""))
        self._subfolder_check.setChecked(self._config.get("include_subfolders", False))
        self._hash_check.setChecked(self._config.get("hash_verify", False))

    # ------------------------------------------------------------------
    def _on_compare(self) -> None:
        src = self._src_edit.text().strip()
        dst = self._dst_edit.text().strip()
        if not src or not dst:
            self._status_label.setText("Set both Source and Destination folders first.")
            return
        if not Path(src).is_dir():
            self._status_label.setText("Source folder does not exist.")
            return

        self._save_config()
        self._set_busy(True)
        self._clear_table()
        self._report_btn.setEnabled(False)
        self._log.clear()
        reverse = self._reverse_radio.isChecked()
        self._status_label.setText("Comparing...")
        self._log.appendPlainText("Starting compare...")

        self._worker = SyncWorker(
            mode="reverse" if reverse else "compare",
            source=src,
            dest=dst,
            recursive=self._subfolder_check.isChecked(),
            file_mask=self._mask_edit.text().strip(),
            hash_verify=self._hash_check.isChecked(),
        )
        self._worker.log.connect(self._on_log)
        self._worker.compare_done.connect(self._on_compare_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_compare_done(self, diff_files: list) -> None:
        self._diff_files = diff_files
        self._set_busy(False)
        self._populate_table(diff_files)
        count = len(diff_files)
        reverse = self._reverse_radio.isChecked()
        if count == 0:
            msg = "No extra files in Destination." if reverse else "Destination is already up to date — nothing to copy."
            self._status_label.setText(msg)
            self._sync_btn.setEnabled(False)
        else:
            noun = "extra file(s) in Destination" if reverse else "file(s) to sync"
            self._status_label.setText(f"{count} {noun}.")
            self._sync_btn.setEnabled(True)
            if self._watch_check.isChecked() and not reverse:
                self._log.appendPlainText("Watch mode: auto-syncing detected changes...")
                self._on_sync()

    # ------------------------------------------------------------------
    def _on_sync(self) -> None:
        if not self._diff_files:
            return
        reverse = self._reverse_radio.isChecked()

        if reverse:
            reply = QMessageBox.warning(
                self, "Delete Extra Files",
                f"Permanently delete {len(self._diff_files)} file(s) from Destination?\n\n"
                "This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._set_busy(True, show_progress=True)
        self._log.clear()
        self._progress.setValue(0)
        self._progress.setMaximum(len(self._diff_files))
        self._status_label.setText("Deleting..." if reverse else "Syncing...")

        self._worker = SyncWorker(
            mode="delete" if reverse else "copy",
            source=self._src_edit.text().strip(),
            dest=self._dst_edit.text().strip(),
            recursive=self._subfolder_check.isChecked(),
            missing_files=self._diff_files,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.copy_done.connect(lambda files: self._on_action_done(files, "Copied"))
        self._worker.delete_done.connect(lambda files: self._on_action_done(files, "Deleted"))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        self._progress.setValue(current)
        verb = "Deleting" if self._reverse_radio.isChecked() else "Copying"
        self._status_label.setText(f"{verb} {current} / {total}...")

    def _on_log(self, msg: str) -> None:
        self._log.appendPlainText(msg)

    def _on_action_done(self, files: list, action: str) -> None:
        self._set_busy(False, show_progress=False)
        total = len(files)
        self._last_report = files
        self._last_action = action
        self._diff_files = []
        self._progress.setValue(0)
        verb = action.lower()
        self._status_label.setText(f"Done — {total} file(s) {verb}.")
        self._sync_btn.setEnabled(False)
        self._report_btn.setEnabled(total > 0)
        self._log.appendPlainText(f"\n{action}: {total} file(s).")

    # ------------------------------------------------------------------
    def _on_export_report(self) -> None:
        if not self._last_report:
            return
        default_name = f"foldersync_report_{self._last_action.lower()}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export Report", default_name, "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Action", "Name", "Size", "Relative Path"])
                for info in self._last_report:
                    writer.writerow([self._last_action, info["name"], info["size"], info["rel_path"]])
            self._status_label.setText(f"Report exported to {path}")
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not write report:\n{exc}")

    # ------------------------------------------------------------------
    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        self._set_busy(False, show_progress=False)
        self._progress.setValue(0)
        self._status_label.setText("Cancelled.")

    def _on_error(self, msg: str) -> None:
        self._set_busy(False, show_progress=False)
        self._progress.setValue(0)
        self._status_label.setText(f"Error: {msg}")
        self._log.appendPlainText(f"ERROR: {msg}")

    def _on_clear(self) -> None:
        self._clear_table()
        self._log.clear()
        self._diff_files = []
        self._report_btn.setEnabled(False)
        self._status_label.setText("Ready")
        self._sync_btn.setEnabled(False)

    # ------------------------------------------------------------------
    def _populate_table(self, files: list) -> None:
        reverse = self._reverse_radio.isChecked()
        path_key = "dst_path" if reverse else "src_path"
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(files))
        for row, info in enumerate(files):
            self._table.setItem(row, 0, QTableWidgetItem(info["name"]))
            size_item = QTableWidgetItem(_fmt_size(info["size"]))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 1, size_item)
            self._table.setItem(row, 2, QTableWidgetItem(info.get("reason", "")))
            self._table.setItem(row, 3, QTableWidgetItem(info.get(path_key, "")))
        self._table.setSortingEnabled(True)

    def _clear_table(self) -> None:
        self._table.setRowCount(0)

    def _set_busy(self, busy: bool, show_progress: bool = False) -> None:
        self._compare_btn.setEnabled(not busy)
        self._sync_btn.setEnabled(not busy)
        self._clear_btn.setEnabled(not busy)
        self._cancel_btn.setVisible(busy)

    def _save_config(self) -> None:
        self._config.set("source_path", self._src_edit.text().strip())
        self._config.set("dest_path", self._dst_edit.text().strip())
        self._config.set("include_subfolders", self._subfolder_check.isChecked())
        self._config.set("file_mask", self._mask_edit.text().strip())
        self._config.set("hash_verify", self._hash_check.isChecked())
        self._config.save()

    # ------------------------------------------------------------------
    # Sync profiles
    def _refresh_profile_combo(self) -> None:
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        self._profile_combo.addItem(self._NO_PROFILE)
        self._profile_combo.addItems(self._profiles.names())
        self._profile_combo.blockSignals(False)

    def _on_profile_selected(self, name: str) -> None:
        if not name or name == self._NO_PROFILE:
            return
        values = self._profiles.get(name)
        if not values:
            return
        self._src_edit.setText(values.get("source", ""))
        self._dst_edit.setText(values.get("dest", ""))
        self._subfolder_check.setChecked(values.get("recursive", False))
        self._mask_edit.setText(values.get("file_mask", ""))
        self._hash_check.setChecked(values.get("hash_verify", False))
        self._status_label.setText(f"Loaded profile '{name}'.")

    def _on_save_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        name = name.strip()
        if not ok or not name:
            return
        values = {
            "source": self._src_edit.text().strip(),
            "dest": self._dst_edit.text().strip(),
            "recursive": self._subfolder_check.isChecked(),
            "file_mask": self._mask_edit.text().strip(),
            "hash_verify": self._hash_check.isChecked(),
        }
        self._profiles.save_profile(name, values)
        self._refresh_profile_combo()
        self._profile_combo.setCurrentText(name)
        self._status_label.setText(f"Profile '{name}' saved.")

    def _on_delete_profile(self) -> None:
        name = self._profile_combo.currentText()
        if not name or name == self._NO_PROFILE:
            return
        reply = QMessageBox.question(
            self, "Delete Profile", f"Delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._profiles.delete_profile(name)
        self._refresh_profile_combo()
        self._status_label.setText(f"Profile '{name}' deleted.")

    # ------------------------------------------------------------------
    # Watch mode
    def _on_watch_toggled(self, enabled: bool) -> None:
        if enabled:
            src = self._src_edit.text().strip()
            if not src or not Path(src).is_dir():
                self._status_label.setText("Set a valid Source folder before enabling Watch mode.")
                self._watch_check.setChecked(False)
                return
            self._start_watching(src)
        else:
            self._stop_watching()

    def _start_watching(self, src: str) -> None:
        self._stop_watching()
        self._watcher = QFileSystemWatcher(self)
        dirs = [src]
        if self._subfolder_check.isChecked():
            dirs.extend(str(p) for p in Path(src).rglob("*") if p.is_dir())
        self._watcher.addPaths(dirs)
        self._watcher.directoryChanged.connect(self._on_source_changed)
        self._status_label.setText(f"Watching {src} for changes...")

    def _stop_watching(self) -> None:
        if self._watcher is not None:
            self._watcher.deleteLater()
            self._watcher = None
        self._watch_timer.stop()

    def _on_source_changed(self, _path: str) -> None:
        self._watch_timer.start(self._WATCH_DEBOUNCE_MS)

    def _on_watch_triggered(self) -> None:
        if self._worker and self._worker.isRunning():
            self._watch_timer.start(self._WATCH_DEBOUNCE_MS)
            return
        self._log.appendPlainText("\nWatch mode: change detected, re-syncing...")
        self._on_compare()

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        self._config.set("window_size", [self.width(), self.height()])
        self._save_config()
        self._stop_watching()
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        event.accept()
