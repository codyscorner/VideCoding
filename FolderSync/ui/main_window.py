from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
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

    def __init__(self, config, base_dir: Path, version: str):
        super().__init__()
        self._config = config
        self._base_dir = base_dir
        self._version = version
        self._worker: SyncWorker | None = None
        self._missing_files: list = []

        self.setWindowTitle(f"Folder Sync v{version}")
        w, h = self._config.get("window_size", [900, 700])
        self.resize(w, h)

        self._build_ui()
        self._load_saved_paths()

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

        # Source row
        layout.addWidget(self._path_row("Source:", "_src_edit", "_src_browse"))

        # Destination row
        layout.addWidget(self._path_row("Destination:", "_dst_edit", "_dst_browse"))

        # Options row
        opt_row = QHBoxLayout()
        self._subfolder_check = QCheckBox("Include subfolders")
        self._subfolder_check.setChecked(self._config.get("include_subfolders", False))
        opt_row.addWidget(self._subfolder_check)
        opt_row.addStretch()
        opt_widget = QWidget()
        opt_widget.setLayout(opt_row)
        layout.addWidget(opt_widget)

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
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(100)
        self._clear_btn.setObjectName("browse")
        self._clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self._compare_btn)
        btn_row.addWidget(self._sync_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._clear_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_row)
        layout.addWidget(btn_widget)

        # Status label
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("status")
        layout.addWidget(self._status_label)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Name", "Size", "Source Path"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 220)
        self._table.setColumnWidth(1, 80)
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

    def _load_saved_paths(self) -> None:
        self._src_edit.setText(self._config.get("source_path", ""))
        self._dst_edit.setText(self._config.get("dest_path", ""))
        self._mask_edit.setText(self._config.get("file_mask", ""))
        self._subfolder_check.setChecked(self._config.get("include_subfolders", False))

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
        self._log.clear()
        self._status_label.setText("Comparing...")
        self._log.appendPlainText("Starting compare...")

        self._worker = SyncWorker(
            mode="compare",
            source=src,
            dest=dst,
            recursive=self._subfolder_check.isChecked(),
            file_mask=self._mask_edit.text().strip(),
        )
        self._worker.log.connect(self._on_log)
        self._worker.compare_done.connect(self._on_compare_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_compare_done(self, missing: list) -> None:
        self._missing_files = missing
        self._set_busy(False)
        self._populate_table(missing)
        count = len(missing)
        if count == 0:
            self._status_label.setText("Destination is already up to date — nothing to copy.")
            self._sync_btn.setEnabled(False)
        else:
            self._status_label.setText(f"{count} file(s) missing from Destination.")
            self._sync_btn.setEnabled(True)

    # ------------------------------------------------------------------
    def _on_sync(self) -> None:
        if not self._missing_files:
            return
        self._set_busy(True, show_progress=True)
        self._log.clear()
        self._progress.setValue(0)
        self._progress.setMaximum(len(self._missing_files))
        self._status_label.setText("Syncing...")

        self._worker = SyncWorker(
            mode="copy",
            source=self._src_edit.text().strip(),
            dest=self._dst_edit.text().strip(),
            recursive=self._subfolder_check.isChecked(),
            missing_files=self._missing_files,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.copy_done.connect(self._on_copy_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        self._progress.setValue(current)
        self._status_label.setText(f"Copying {current} / {total}...")

    def _on_log(self, msg: str) -> None:
        self._log.appendPlainText(msg)

    def _on_copy_done(self) -> None:
        self._set_busy(False, show_progress=False)
        total = len(self._missing_files)
        self._missing_files = []
        self._progress.setValue(0)
        self._status_label.setText(f"Done — {total} file(s) copied.")
        self._sync_btn.setEnabled(False)
        self._log.appendPlainText(f"\nSync complete. {total} file(s) copied.")

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
        self._missing_files = []
        self._status_label.setText("Ready")
        self._sync_btn.setEnabled(False)

    # ------------------------------------------------------------------
    def _populate_table(self, files: list) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(files))
        for row, info in enumerate(files):
            self._table.setItem(row, 0, QTableWidgetItem(info["name"]))
            size_item = QTableWidgetItem(_fmt_size(info["size"]))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 1, size_item)
            self._table.setItem(row, 2, QTableWidgetItem(info["src_path"]))
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
        self._config.save()

    def closeEvent(self, event) -> None:
        self._config.set("window_size", [self.width(), self.height()])
        self._save_config()
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        event.accept()
