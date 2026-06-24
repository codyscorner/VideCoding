from __future__ import annotations

import json
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from worker import ConversionWorker

CONFIG_FILE = Path(__file__).parent.parent / "video_converter_config.json"

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".ts", ".mpg", ".mpeg",
}

PRESETS = [
    {
        "label": "AVI — Xvid (widest photo frame compatibility)",
        "ext": ".avi",
        "args": ["-vcodec", "libxvid", "-q:v", "4", "-acodec", "mp3", "-q:a", "4"],
    },
    {
        "label": "MP4 — H.264 Baseline (maximum device compatibility)",
        "ext": ".mp4",
        "args": [
            "-vcodec", "libx264",
            "-profile:v", "baseline",
            "-level", "3.1",
            "-pix_fmt", "yuv420p",
            "-acodec", "aac",
            "-b:a", "128k",
        ],
    },
    {
        "label": "MP4 — H.264 High (modern TVs, phones, PC players)",
        "ext": ".mp4",
        "args": [
            "-vcodec", "libx264",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-acodec", "aac",
            "-b:a", "128k",
        ],
    },
    {
        "label": "MP4 — H.265 / HEVC (newer devices, ~50% smaller files)",
        "ext": ".mp4",
        "args": [
            "-vcodec", "libx265",
            "-pix_fmt", "yuv420p",
            "-acodec", "aac",
            "-b:a", "128k",
        ],
    },
    {
        "label": "MP4 — MPEG-4 Part 2 (very old devices / frames without H.264)",
        "ext": ".mp4",
        "args": [
            "-vcodec", "mpeg4",
            "-vtag", "xvid",
            "-q:v", "4",
            "-pix_fmt", "yuv420p",
            "-acodec", "aac",
            "-b:a", "128k",
        ],
    },
    {
        "label": "MOV — H.264 (QuickTime / Apple devices)",
        "ext": ".mov",
        "args": ["-vcodec", "libx264", "-pix_fmt", "yuv420p", "-acodec", "aac", "-b:a", "128k"],
    },
]

STATUS_PENDING    = "Pending"
STATUS_CONVERTING = "Converting..."
STATUS_DONE       = "Done"
STATUS_ERROR      = "Error"

COLOR_PENDING    = "#606080"
COLOR_CONVERTING = "#d0b030"
COLOR_DONE       = "#40c060"
COLOR_ERROR      = "#c04040"

STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0f0;
    font-size: 13px;
}
QFrame#drop_zone {
    border: 2px dashed #3a3a6a;
    border-radius: 8px;
    background-color: #14142a;
}
QFrame#drop_zone[drag_active="true"] {
    border: 2px dashed #5294e2;
    background-color: #1a2248;
}
QTableWidget {
    background-color: #12122a;
    alternate-background-color: #16163a;
    gridline-color: #2a2a50;
    color: #e0e0f0;
    border: 1px solid #2a2a50;
    border-radius: 4px;
}
QTableWidget::item {
    padding: 4px 8px;
}
QTableWidget::item:selected {
    background-color: #303060;
}
QHeaderView::section {
    background-color: #16163a;
    color: #8080b0;
    border: none;
    border-bottom: 1px solid #2a2a50;
    padding: 5px 8px;
    font-weight: bold;
}
QPushButton {
    background-color: #252550;
    color: #e0e0f0;
    border: 1px solid #3a3a7a;
    border-radius: 4px;
    padding: 6px 14px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #303070;
    border-color: #5050a0;
}
QPushButton:pressed {
    background-color: #181840;
}
QPushButton:disabled {
    background-color: #16163a;
    color: #444466;
    border-color: #252550;
}
QPushButton#convert_btn {
    background-color: #1e4d1e;
    border-color: #2e7a2e;
    font-weight: bold;
    min-width: 120px;
}
QPushButton#convert_btn:hover {
    background-color: #286228;
}
QPushButton#convert_btn:disabled {
    background-color: #141e14;
    color: #3a5a3a;
    border-color: #1e3a1e;
}
QPushButton#cancel_btn {
    background-color: #4d1e1e;
    border-color: #7a2e2e;
    min-width: 100px;
}
QPushButton#cancel_btn:hover {
    background-color: #622828;
}
QPushButton#cancel_btn:disabled {
    background-color: #1e1414;
    color: #5a3a3a;
    border-color: #3a1e1e;
}
QComboBox {
    background-color: #14142a;
    color: #e0e0f0;
    border: 1px solid #3a3a7a;
    border-radius: 4px;
    padding: 5px 8px;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a3a;
    color: #e0e0f0;
    border: 1px solid #3a3a7a;
    selection-background-color: #303060;
}
QLineEdit {
    background-color: #14142a;
    color: #e0e0f0;
    border: 1px solid #3a3a7a;
    border-radius: 4px;
    padding: 5px 8px;
}
QGroupBox {
    border: 1px solid #2a2a50;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #6060a0;
}
QProgressBar {
    background-color: #12122a;
    border: 1px solid #3a3a7a;
    border-radius: 4px;
    text-align: center;
    color: #e0e0f0;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #5294e2;
    border-radius: 3px;
}
QTextEdit {
    background-color: #0c0c1a;
    color: #7070a0;
    border: 1px solid #2a2a50;
    border-radius: 4px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 11px;
}
QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a6a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1a1a2e;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #3a3a6a;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


class _DropZone(QFrame):
    """Visual drop target that forwards dropped paths to the parent window."""

    def __init__(self, parent: "MainWindow"):
        super().__init__(parent)
        self._win = parent
        self.setObjectName("drop_zone")
        self.setAcceptDrops(True)
        self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        self._title = QLabel("Drop video files here")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("color: #5050a0; font-size: 16px; border: none;")
        layout.addWidget(self._title)

        hint = QLabel("Single files, multiple files, or drag a folder (top level only)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #383858; font-size: 11px; border: none;")
        layout.addWidget(hint)

    def update_count(self, n: int):
        self._title.setText(
            "Drop video files here" if n == 0
            else f"{n} file{'s' if n != 1 else ''} queued — drop more to add"
        )

    # --- drag/drop events ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, event):
        self._set_active(False)

    def dropEvent(self, event: QDropEvent):
        self._set_active(False)
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
        self._win._handle_paths(paths)

    def _set_active(self, active: bool):
        self.setProperty("drag_active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, version: str):
        super().__init__()
        self.setWindowTitle(f"Video Converter  v{version}")
        self.resize(940, 720)
        self.setMinimumSize(700, 500)
        self.setStyleSheet(STYLE)

        self._files: list[Path] = []          # ordered list of unique input paths
        self._job_to_row: dict[int, int] = {} # job index → table row
        self._worker: ConversionWorker | None = None

        self._build_ui()
        self._load_config()

    # ------------------------------------------------------------------
    # UI construction

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # Drop zone
        self._drop_zone = _DropZone(self)
        root.addWidget(self._drop_zone)

        # Browse / clear buttons
        btn_row = QHBoxLayout()
        self._browse_files_btn = QPushButton("Browse Files…")
        self._browse_files_btn.clicked.connect(self._browse_files)
        self._browse_folder_btn = QPushButton("Browse Folder…")
        self._browse_folder_btn.clicked.connect(self._browse_folder)
        btn_row.addWidget(self._browse_files_btn)
        btn_row.addWidget(self._browse_folder_btn)
        btn_row.addStretch()
        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self._clear_btn)
        root.addLayout(btn_row)

        # File table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Source File", "Output File", "Status"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 120)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table, 1)

        # Settings
        settings = QGroupBox("Settings")
        sg = QVBoxLayout(settings)
        sg.setSpacing(6)
        sg.setContentsMargins(10, 12, 10, 8)

        # Format preset
        fmt_row = QHBoxLayout()
        fmt_lbl = QLabel("Format:")
        fmt_lbl.setFixedWidth(110)
        fmt_row.addWidget(fmt_lbl)
        self._preset_combo = QComboBox()
        for p in PRESETS:
            self._preset_combo.addItem(p["label"])
        self._preset_combo.currentIndexChanged.connect(self._rebuild_output_names)
        fmt_row.addWidget(self._preset_combo, 1)
        sg.addLayout(fmt_row)

        # Output folder
        out_row = QHBoxLayout()
        out_lbl = QLabel("Output Folder:")
        out_lbl.setFixedWidth(110)
        out_row.addWidget(out_lbl)
        self._out_dir_edit = QLineEdit()
        self._out_dir_edit.setPlaceholderText("(same as source file)")
        self._out_dir_edit.textChanged.connect(self._rebuild_output_names)
        out_row.addWidget(self._out_dir_edit, 1)
        out_browse = QPushButton("Browse…")
        out_browse.setFixedWidth(80)
        out_browse.clicked.connect(self._browse_out_dir)
        out_row.addWidget(out_browse)
        sg.addLayout(out_row)

        # Suffix
        sfx_row = QHBoxLayout()
        sfx_lbl = QLabel("Suffix:")
        sfx_lbl.setFixedWidth(110)
        sfx_row.addWidget(sfx_lbl)
        self._suffix_edit = QLineEdit()
        self._suffix_edit.setPlaceholderText("(none — keep original filename, just change extension)")
        self._suffix_edit.textChanged.connect(self._rebuild_output_names)
        sfx_row.addWidget(self._suffix_edit, 1)
        sg.addLayout(sfx_row)

        # FFmpeg path
        ffmpeg_row = QHBoxLayout()
        ffmpeg_lbl = QLabel("FFmpeg Path:")
        ffmpeg_lbl.setFixedWidth(110)
        ffmpeg_row.addWidget(ffmpeg_lbl)
        self._ffmpeg_edit = QLineEdit()
        self._ffmpeg_edit.setPlaceholderText("ffmpeg  (if on PATH) — or browse to ffmpeg.exe")
        self._ffmpeg_edit.textChanged.connect(self._save_config)
        ffmpeg_row.addWidget(self._ffmpeg_edit, 1)
        ffmpeg_browse = QPushButton("Browse…")
        ffmpeg_browse.setFixedWidth(80)
        ffmpeg_browse.clicked.connect(self._browse_ffmpeg)
        ffmpeg_row.addWidget(ffmpeg_browse)
        sg.addLayout(ffmpeg_row)

        root.addWidget(settings)

        # Action row
        action = QHBoxLayout()
        self._convert_btn = QPushButton("▶   Convert")
        self._convert_btn.setObjectName("convert_btn")
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self._start_conversion)
        self._cancel_btn = QPushButton("✕   Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_conversion)
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setFormat("")
        self._prog_label = QLabel("—")
        self._prog_label.setStyleSheet("color: #5050a0; min-width: 55px; text-align: right;")
        self._prog_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        action.addWidget(self._convert_btn)
        action.addWidget(self._cancel_btn)
        action.addSpacing(8)
        action.addWidget(self._progress, 1)
        action.addWidget(self._prog_label)
        root.addLayout(action)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(130)
        self._log.setMinimumHeight(80)
        root.addWidget(self._log)

    # ------------------------------------------------------------------
    # Input handling

    def _handle_paths(self, paths: list[Path]):
        """Accept a mix of files and folders; folders are scanned one level deep."""
        candidates: list[Path] = []
        for p in paths:
            if p.is_dir():
                candidates.extend(
                    f for f in sorted(p.iterdir())
                    if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
                )
            elif p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                candidates.append(p)
        self._add_files(candidates)

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.ts *.mpg *.mpeg)"
            ";;All Files (*.*)",
        )
        self._add_files([Path(p) for p in paths])

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Convert")
        if not folder:
            return
        videos = sorted(
            f for f in Path(folder).iterdir()
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
        )
        self._add_files(videos)

    def _browse_out_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self._out_dir_edit.setText(folder)

    def _browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Locate ffmpeg.exe", "", "Executable (*.exe);;All Files (*.*)"
        )
        if path:
            self._ffmpeg_edit.setText(path)

    # ------------------------------------------------------------------
    # Config persistence

    def _load_config(self):
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        ffmpeg = data.get("ffmpeg_path", "")
        if not ffmpeg:
            ffmpeg = self._auto_find_ffmpeg()
        self._ffmpeg_edit.setText(ffmpeg)

    @staticmethod
    def _auto_find_ffmpeg() -> str:
        # 1. Check PATH
        found = shutil.which("ffmpeg")
        if found:
            return found

        # 2. Check Chain Automator config (sibling app in the same repo)
        chain_cfg = Path(__file__).parent.parent.parent / "ComfyUI_Chain_Automator" / "main_config.json"
        try:
            data = json.loads(chain_cfg.read_text(encoding="utf-8"))
            p = Path(data.get("ffmpeg_path", ""))
            if p.exists():
                return str(p)
        except Exception:
            pass

        # 3. Scan all venvs under known Python/pip roots for imageio_ffmpeg binaries
        search_roots = [
            Path("C:/AI"),
            Path("C:/Users") / Path(__file__).parts[2] / "AppData/Local/Programs/Python",
            Path("P:/AI"),
        ]
        for root in search_roots:
            if not root.exists():
                continue
            for exe in root.rglob("ffmpeg-win-x86_64*.exe"):
                return str(exe)
            for exe in root.rglob("ffmpeg.exe"):
                return str(exe)

        return ""

    def _save_config(self):
        data = {"ffmpeg_path": self._ffmpeg_edit.text().strip()}
        try:
            CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _add_files(self, paths: list[Path]):
        existing = set(self._files)
        new = [p for p in paths if p not in existing]
        if not new:
            return
        self._files.extend(new)
        for p in new:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(p.name))
            self._table.setItem(row, 1, QTableWidgetItem(self._output_name_for(p)))
            status = QTableWidgetItem(STATUS_PENDING)
            status.setForeground(QColor(COLOR_PENDING))
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, status)
        self._drop_zone.update_count(len(self._files))
        self._convert_btn.setEnabled(True)

    def _clear_files(self):
        self._files.clear()
        self._table.setRowCount(0)
        self._drop_zone.update_count(0)
        self._convert_btn.setEnabled(False)
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._prog_label.setText("—")

    # ------------------------------------------------------------------
    # Output name helpers

    def _output_name_for(self, input_path: Path) -> str:
        ext = PRESETS[self._preset_combo.currentIndex()]["ext"]
        suffix = self._suffix_edit.text().strip()
        stem = input_path.stem
        return f"{stem}_{suffix}{ext}" if suffix else f"{stem}{ext}"

    def _output_path_for(self, input_path: Path) -> Path:
        out_name = self._output_name_for(input_path)
        out_dir_text = self._out_dir_edit.text().strip()
        out_dir = Path(out_dir_text) if out_dir_text else input_path.parent
        return out_dir / out_name

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        i = 1
        while True:
            candidate = path.parent / f"{path.stem}_{i}{path.suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def _rebuild_output_names(self):
        for row, p in enumerate(self._files):
            item = self._table.item(row, 1)
            if item:
                item.setText(self._output_name_for(p))

    # ------------------------------------------------------------------
    # Conversion

    def _start_conversion(self):
        # Reset any previously Converting/Error rows back to Pending
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 2)
            if item and item.text() in (STATUS_CONVERTING, STATUS_ERROR):
                item.setText(STATUS_PENDING)
                item.setForeground(QColor(COLOR_PENDING))

        # Build job list — skip already-Done rows
        jobs: list[dict] = []
        self._job_to_row = {}
        preset_args = PRESETS[self._preset_combo.currentIndex()]["args"]

        for row, p in enumerate(self._files):
            status_item = self._table.item(row, 2)
            if status_item and status_item.text() == STATUS_DONE:
                continue
            out = self._unique_path(self._output_path_for(p))
            # reflect any collision-resolved name in the table
            out_item = self._table.item(row, 1)
            if out_item:
                out_item.setText(out.name)
            job_idx = len(jobs)
            self._job_to_row[job_idx] = row
            jobs.append({"input": p, "output": out, "args": list(preset_args)})

        if not jobs:
            self._log_append("Nothing to convert (all files already done).")
            return

        self._log.clear()
        self._progress.setRange(0, len(jobs))
        self._progress.setValue(0)
        self._prog_label.setText(f"0 / {len(jobs)}")

        self._set_controls_busy(True)

        ffmpeg_path = self._ffmpeg_edit.text().strip() or "ffmpeg"
        self._worker = ConversionWorker(jobs, ffmpeg_path=ffmpeg_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.log.connect(self._log_append)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel_conversion(self):
        if self._worker:
            self._worker.cancel()

    # ------------------------------------------------------------------
    # Worker slots

    @pyqtSlot(int, int)
    def _on_progress(self, job_idx: int, total: int):
        self._progress.setValue(job_idx)
        self._prog_label.setText(f"{job_idx} / {total}")
        if job_idx < total:
            self._set_row_status(job_idx, STATUS_CONVERTING, COLOR_CONVERTING)

    @pyqtSlot(int, bool, str)
    def _on_file_done(self, job_idx: int, success: bool, _msg: str):
        if success:
            self._set_row_status(job_idx, STATUS_DONE, COLOR_DONE)
        else:
            self._set_row_status(job_idx, STATUS_ERROR, COLOR_ERROR)

    @pyqtSlot(int, int)
    def _on_finished(self, done: int, failed: int):
        total = self._progress.maximum()
        self._progress.setValue(total)
        self._prog_label.setText(f"{done} / {total}")

        summary = f"Done — {done} converted"
        if failed:
            summary += f", {failed} failed"
        self._log_append(f"\n{summary}")

        self._set_controls_busy(False)
        self._worker = None

    # ------------------------------------------------------------------
    # Helpers

    def _set_row_status(self, job_idx: int, text: str, color: str):
        row = self._job_to_row.get(job_idx)
        if row is None:
            return
        item = self._table.item(row, 2)
        if item:
            item.setText(text)
            item.setForeground(QColor(color))

    def _set_controls_busy(self, busy: bool):
        self._convert_btn.setEnabled(not busy and bool(self._files))
        self._cancel_btn.setEnabled(busy)
        self._browse_files_btn.setEnabled(not busy)
        self._browse_folder_btn.setEnabled(not busy)
        self._clear_btn.setEnabled(not busy)
        self._preset_combo.setEnabled(not busy)

    def _log_append(self, text: str):
        self._log.append(text)
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())
