import os
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.archiver import COMPRESSION_FLAGS, DEFAULT_PREFIX, build_archive_name, run_archive
from utils.logger import create_log_file, write_log
from utils.settings_manager import DEFAULT_PREFIX, get_app_dir, load_settings, save_settings
from utils.verifier import generate_sha256, run_integrity_test

# ── Stylesheet ────────────────────────────────────────────────────────────────

STYLE = """
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    color: #58a6ff;
    font-size: 10pt;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QLineEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e6edf3;
}
QLineEdit:focus {
    border-color: #1f6feb;
}
QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e6edf3;
}
QComboBox:focus {
    border-color: #1f6feb;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    color: #e6edf3;
}
QPushButton {
    background-color: #1f6feb;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #388bfd;
}
QPushButton:pressed {
    background-color: #1158c7;
}
QPushButton:disabled {
    background-color: #21262d;
    color: #484f58;
}
QPushButton#btn_secondary {
    background-color: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
}
QPushButton#btn_secondary:hover {
    background-color: #30363d;
    border-color: #58a6ff;
}
QPushButton#btn_cancel {
    background-color: #21262d;
    border: 1px solid #f85149;
    color: #f85149;
}
QPushButton#btn_cancel:hover {
    background-color: #3d1a1a;
}
QProgressBar {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    height: 22px;
    text-align: center;
    color: #e6edf3;
    font-size: 9pt;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 3px;
}
QListWidget {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px;
    font-family: 'Consolas';
    font-size: 9pt;
}
QListWidget::item {
    padding: 2px 4px;
}
QScrollBar:vertical {
    background: #161b22;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #58a6ff;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
"""

# ── Compression options ───────────────────────────────────────────────────────

COMPRESSION_OPTIONS = [
    ("Store — no compression  (photos, videos, already-compressed files)", "store"),
    ("Fast — level 3  (quick backup, light compression)",                   "fast"),
    ("Normal — level 5  (balanced)",                                        "normal"),
    ("Maximum — level 7  (documents, text files)",                          "maximum"),
    ("Ultra — level 9  (best compression, slowest)",                        "ultra"),
]

# ── Worker Thread ─────────────────────────────────────────────────────────────

class BackupWorker(QThread):
    progress = pyqtSignal(int)
    log_msg  = pyqtSignal(str)
    status   = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, settings, source_folder, dest_path, prefix=None, compression="store"):
        super().__init__()
        self.settings      = settings
        self.source_folder = source_folder
        self.dest_path     = dest_path
        self.prefix        = prefix
        self.compression   = compression
        self._cancelled    = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        seven_zip = self.settings.get("7zip_path", "")
        app_dir   = get_app_dir()
        log_path  = create_log_file(app_dir)

        start_time = datetime.now()

        def elapsed():
            secs = int((datetime.now() - start_time).total_seconds())
            return f"[{secs // 3600:02d}:{(secs % 3600) // 60:02d}:{secs % 60:02d}]"

        def log(msg):
            self.log_msg.emit(f"{elapsed()} {msg}")
            write_log(log_path, msg)

        def archive_progress(pct):
            self.progress.emit(int(pct * 0.75))

        # ── Phase 1: Archive ──────────────────────────────────────────────
        self.status.emit("Creating archive...")
        log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        success, archive_path, error = run_archive(
            seven_zip,
            self.source_folder,
            self.dest_path,
            archive_progress,
            log,
            cancel_check=lambda: self._cancelled,
            prefix=self.prefix,
            compression=self.compression,
        )

        if self._cancelled:
            log("Backup cancelled by user.")
            self.status.emit("Cancelled.")
            self.finished.emit(False, "Backup cancelled.")
            return

        if not success:
            log(f"Archive FAILED: {error}")
            self.status.emit("Archive failed.")
            self.finished.emit(False, f"Archive failed:\n{error}")
            return

        log("Archive created successfully.")
        self.progress.emit(75)

        # ── Phase 2: Integrity test ───────────────────────────────────────
        self.status.emit("Verifying archive integrity...")
        ok = run_integrity_test(seven_zip, archive_path, log)
        if not ok:
            self.status.emit("Integrity test failed.")
            self.finished.emit(False, "Archive integrity test failed.")
            return

        self.progress.emit(90)

        # ── Phase 3: SHA-256 ──────────────────────────────────────────────
        self.status.emit("Generating SHA-256 hash...")
        generate_sha256(archive_path, log)
        self.progress.emit(100)

        # ── Save settings ─────────────────────────────────────────────────
        self.settings["last_source_folder"]  = self.source_folder
        self.settings["last_destination_path"] = self.dest_path
        self.settings["last_archive_date"]   = datetime.now().strftime("%Y-%m-%d")
        self.settings["compression_level"]   = self.compression
        if self.prefix:
            self.settings["archive_prefix"] = self.prefix
        save_settings(self.settings)

        log(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"Log: {os.path.basename(log_path)}")

        total = int((datetime.now() - start_time).total_seconds())
        elapsed_str = f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

        self.status.emit("Backup complete!")
        self.finished.emit(
            True,
            f"Backup complete!\n\n"
            f"{archive_path}\n\n"
            f"Total elapsed time:  {elapsed_str}"
        )


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker   = None
        self._build_ui()
        self._load_from_settings()
        self._check_7zip()

    def _build_ui(self):
        self.setWindowTitle("Folder Backup Archiver")
        self.setMinimumSize(760, 800)
        self.resize(760, 820)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        # Header
        title = QLabel("Folder Backup Archiver")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #58a6ff; margin-bottom: 2px;")

        subtitle = QLabel("7-Zip archive  ·  SHA-256 verified  ·  Daily dated filename")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7d8590; font-size: 9pt;")

        root.addWidget(title)
        root.addWidget(subtitle)

        # ── Source folder ─────────────────────────────────────────────────
        src_group = QGroupBox("Source Folder")
        src_row = QHBoxLayout(src_group)
        src_row.setSpacing(8)
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Select folder to archive...")
        btn_browse_src = QPushButton("Browse")
        btn_browse_src.setObjectName("btn_secondary")
        btn_browse_src.setFixedWidth(80)
        btn_browse_src.clicked.connect(self._browse_source)
        src_row.addWidget(self.source_edit)
        src_row.addWidget(btn_browse_src)
        root.addWidget(src_group)

        # ── Destination path ──────────────────────────────────────────────
        dst_group = QGroupBox("Destination  (local drive, mapped drive, or UNC path)")
        dst_row = QHBoxLayout(dst_group)
        dst_row.setSpacing(8)
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("e.g.  E:\\Backups\\   or   \\\\NAS1\\Backups\\")
        btn_browse_dst = QPushButton("Browse")
        btn_browse_dst.setObjectName("btn_secondary")
        btn_browse_dst.setFixedWidth(80)
        btn_browse_dst.clicked.connect(self._browse_dest)
        dst_row.addWidget(self.dest_edit)
        dst_row.addWidget(btn_browse_dst)
        root.addWidget(dst_group)

        # ── Archive name ──────────────────────────────────────────────────
        name_group = QGroupBox("Archive Name")
        name_row = QHBoxLayout(name_group)
        name_row.setSpacing(8)

        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("Archive name prefix...")

        from datetime import date as _date
        self._date_suffix = f"_{_date.today().strftime('%Y_%m_%d')}.7z"
        self.suffix_label = QLabel(self._date_suffix)
        self.suffix_label.setStyleSheet(
            "color: #7d8590; font-family: Consolas; font-size: 10pt;"
        )
        self.suffix_label.setFixedWidth(160)

        btn_reset = QPushButton("Reset")
        btn_reset.setObjectName("btn_secondary")
        btn_reset.setFixedWidth(70)
        btn_reset.clicked.connect(self._reset_prefix)

        name_row.addWidget(self.prefix_edit)
        name_row.addWidget(self.suffix_label)
        name_row.addWidget(btn_reset)
        root.addWidget(name_group)

        # ── Compression ───────────────────────────────────────────────────
        comp_group = QGroupBox("Compression")
        comp_row = QHBoxLayout(comp_group)
        comp_row.setSpacing(8)
        self.comp_combo = QComboBox()
        self.comp_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for label, key in COMPRESSION_OPTIONS:
            self.comp_combo.addItem(label, userData=key)
        comp_row.addWidget(self.comp_combo)
        root.addWidget(comp_group)

        # ── Action buttons ────────────────────────────────────────────────
        self.btn_start = QPushButton("Start Backup")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_start.clicked.connect(self._start_backup)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_backup)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_cancel)
        root.addLayout(btn_row)

        # ── Progress ──────────────────────────────────────────────────────
        prog_group = QGroupBox("Progress")
        prog_layout = QVBoxLayout(prog_group)
        prog_layout.setSpacing(6)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7d8590; font-size: 9pt;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setFormat("%p%")

        prog_layout.addWidget(self.status_label)
        prog_layout.addWidget(self.progress_bar)
        root.addWidget(prog_group)

        # ── Log ───────────────────────────────────────────────────────────
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(200)
        log_layout.addWidget(self.log_list)
        root.addWidget(log_group)

    # ── Settings load/save ────────────────────────────────────────────────────

    def _load_from_settings(self):
        src = self.settings.get("last_source_folder", "")
        if src:
            self.source_edit.setText(src)

        # Support old key name (last_destination_drive) for backward compat
        dest = self.settings.get("last_destination_path") or self.settings.get("last_destination_drive", "")
        if dest:
            self.dest_edit.setText(dest)

        prefix = self.settings.get("archive_prefix", DEFAULT_PREFIX)
        self.prefix_edit.setText(prefix)

        saved_comp = self.settings.get("compression_level", "store")
        for i in range(self.comp_combo.count()):
            if self.comp_combo.itemData(i) == saved_comp:
                self.comp_combo.setCurrentIndex(i)
                break

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse_source(self):
        start = self.source_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def _browse_dest(self):
        start = self.dest_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)

    def _reset_prefix(self):
        self.prefix_edit.setText(DEFAULT_PREFIX)

    def _check_7zip(self):
        path = self.settings.get("7zip_path", "")
        if path and os.path.exists(path):
            return

        app_dir = get_app_dir()
        candidates = [
            os.path.join(app_dir, "7z2601-extra", "x64", "7za.exe"),
            os.path.join(app_dir, "7z2601-extra", "7za.exe"),
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                self.settings["7zip_path"] = c
                save_settings(self.settings)
                self._log(f"7-Zip: {c}")
                return

        QMessageBox.warning(
            self,
            "7-Zip Not Found",
            "7-Zip was not found.\n\n"
            "Expected location:\n"
            "  7z2601-extra\\x64\\7za.exe\n\n"
            "Or update '7zip_path' in settings.json.",
        )

    def _start_backup(self):
        source = self.source_edit.text().strip()
        if not source or not os.path.isdir(source):
            QMessageBox.warning(self, "Missing Source", "Please select a valid source folder.")
            return

        dest = self.dest_edit.text().strip()
        if not dest:
            QMessageBox.warning(self, "Missing Destination", "Please enter or browse to a destination path.")
            return
        if not os.path.isdir(dest):
            QMessageBox.warning(
                self, "Invalid Destination",
                f"Destination path not found or inaccessible:\n{dest}"
            )
            return

        seven_zip = self.settings.get("7zip_path", "")
        if not seven_zip or not os.path.exists(seven_zip):
            QMessageBox.critical(self, "7-Zip Not Found", "7-Zip executable not found.\nCheck settings.json.")
            return

        prefix      = self.prefix_edit.text().strip() or DEFAULT_PREFIX
        compression = self.comp_combo.currentData() or "store"

        self.log_list.clear()
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.status_label.setStyleSheet("color: #7d8590; font-size: 9pt;")

        self.worker = BackupWorker(
            self.settings, source, dest,
            prefix=prefix, compression=compression
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log_msg.connect(self._log)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _cancel_backup(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def _log(self, msg):
        item = QListWidgetItem(msg)
        lower = msg.lower()
        if any(w in lower for w in ("failed", "error", "cancelled")):
            item.setForeground(QColor("#f85149"))
        elif any(w in lower for w in ("passed", "complete", "sha-256", "ok", "success")):
            item.setForeground(QColor("#3fb950"))
        elif any(w in msg for w in ("Archive:", "Source:", "Destination:", "Compression:")):
            item.setForeground(QColor("#58a6ff"))
        else:
            item.setForeground(QColor("#c9d1d9"))
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def _on_finished(self, success, message):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setEnabled(True)
        if success:
            self.status_label.setStyleSheet("color: #3fb950; font-size: 9pt;")
            QMessageBox.information(self, "Backup Complete", message)
        else:
            self.status_label.setStyleSheet("color: #f85149; font-size: 9pt;")
            if message != "Backup cancelled.":
                QMessageBox.critical(self, "Backup Failed", message)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
