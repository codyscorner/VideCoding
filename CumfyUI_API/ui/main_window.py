from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit, QRadioButton, QButtonGroup,
    QProgressBar, QListWidget, QListWidgetItem, QGroupBox,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QAbstractItemView, QFileDialog,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from config import ConfigManager
from worker import ChainWorker
from ui.styles import STYLESHEET, COLORS
from ui.video_player import VideoPlayerDialog

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class CompletionDialog(QDialog):
    def __init__(self, final_path: str, parent=None):
        super().__init__(parent)
        self._final_path = final_path
        self.setWindowTitle("Chain Complete!")
        self.setMinimumWidth(520)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        icon = QLabel("✅")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 36pt;")
        layout.addWidget(icon)

        title = QLabel("All 7 segments complete!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #4caf8a;")
        layout.addWidget(title)

        path_label = QLabel(final_path)
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("font-size: 9pt; color: #9090cc;")
        layout.addWidget(path_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        play_btn = QPushButton("▶  Play Video")
        play_btn.setFixedHeight(44)
        play_btn.clicked.connect(self._play)

        skip_btn = QPushButton("✕  Skip")
        skip_btn.setObjectName("cancel_btn")
        skip_btn.setFixedHeight(44)
        skip_btn.clicked.connect(self.accept)

        btn_row.addWidget(play_btn)
        btn_row.addWidget(skip_btn)
        layout.addLayout(btn_row)

    def _play(self):
        self.accept()
        player = VideoPlayerDialog(self._final_path, parent=self.parent())
        player.exec()
THUMB_SIZE = 120


class ImageGrid(QListWidget):
    """Scrollable thumbnail grid for picking the starting image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 24, THUMB_SIZE + 36))
        self.setSpacing(6)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px; }}"
            f"QListWidget::item:selected {{ background-color: {COLORS['accent']}; border-radius: 4px; }}"
        )

    def load_images(self, input_dir: Path):
        self.clear()
        if not input_dir.exists():
            return
        images = sorted(
            p for p in input_dir.iterdir()
            if p.suffix.lower() in IMAGE_EXTS
        )
        for img_path in images:
            pix = QPixmap(str(img_path))
            if pix.isNull():
                continue
            icon = QIcon(pix.scaled(THUMB_SIZE, THUMB_SIZE,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))
            item = QListWidgetItem(icon, img_path.name)
            item.setData(Qt.ItemDataRole.UserRole, img_path.name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            self.addItem(item)

    def selected_image(self) -> str | None:
        items = self.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)


class SegmentDot(QLabel):
    """Small coloured circle showing segment state: pending / active / done."""

    def __init__(self, number: int):
        super().__init__(f" {number} ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(34, 34)
        self.set_pending()

    def _apply(self, bg: str, fg: str):
        self.setStyleSheet(
            f"background-color:{bg}; color:{fg}; border-radius:17px;"
            f" font-weight:bold; font-size:10pt;"
        )

    def set_pending(self):
        self._apply(COLORS['seg_pending'], COLORS['fg_dim'])

    def set_active(self):
        self._apply(COLORS['seg_active'], '#000000')

    def set_done(self):
        self._apply(COLORS['seg_done'], '#000000')


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version
        self._worker: ChainWorker | None = None
        self._seg_dots: list[SegmentDot] = []

        self.setWindowTitle(f"ComfyUI Chain Automator  v{version}")
        self.setMinimumSize(900, 820)
        self.resize(1050, 900)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._populate_images()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header
        header = QLabel("ComfyUI Workflow Chain Automator")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(header)

        subtitle = QLabel("Chains 7 ComfyUI segments automatically, then stitches the final video")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        # ── Mode selector ─────────────────────────────────────────────────
        mode_group = QGroupBox("ComfyUI Server")
        mode_layout = QHBoxLayout(mode_group)

        self._local_radio = QRadioButton("Local")
        self._runpod_radio = QRadioButton("RunPod")
        self._mode_group = QButtonGroup()
        self._mode_group.addButton(self._local_radio)
        self._mode_group.addButton(self._runpod_radio)

        runpod_lbl = QLabel("RunPod URL:")
        self._runpod_url_edit = QLineEdit()
        self._runpod_url_edit.setText(self.config.get("runpod_url", ""))
        self._runpod_url_edit.setPlaceholderText("https://xxxxxx-8188.proxy.runpod.net")

        if self.config.get("mode", "local") == "runpod":
            self._runpod_radio.setChecked(True)
        else:
            self._local_radio.setChecked(True)

        self._local_radio.toggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self._local_radio)
        mode_layout.addWidget(self._runpod_radio)
        mode_layout.addSpacing(20)
        mode_layout.addWidget(runpod_lbl)
        mode_layout.addWidget(self._runpod_url_edit, stretch=1)
        root.addWidget(mode_group)

        # ── Output folder settings (top) ──────────────────────────────────
        paths_group = QGroupBox("Output Folders")
        paths_layout = QVBoxLayout(paths_group)
        paths_layout.setSpacing(8)

        def folder_row(label_text, placeholder, value) -> tuple:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(120)
            edit = QLineEdit()
            edit.setText(value)
            edit.setPlaceholderText(placeholder)
            btn = QPushButton("...")
            btn.setObjectName("browse_btn")
            btn.setFixedWidth(60)
            btn.setFixedHeight(32)
            row.addWidget(lbl)
            row.addWidget(edit, stretch=1)
            row.addWidget(btn)
            paths_layout.addLayout(row)
            return edit, btn

        self.final_dir_edit, final_browse = folder_row(
            "Final Video:", "Folder for stitched video...",
            self.config.get("final_video_dir", "")
        )
        final_browse.clicked.connect(self._browse_final_dir)

        self.zip_edit, zip_browse = folder_row(
            "Archive (.zip):", "Folder for completed zip archives...",
            self.config.get("zip_output_dir", "")
        )
        zip_browse.clicked.connect(self._browse_zip)

        root.addWidget(paths_group)

        # ── Starting image grid ───────────────────────────────────────────
        img_group = QGroupBox("Starting Image  (Segment 1) — click to select")
        img_layout = QVBoxLayout(img_group)
        self.image_grid = ImageGrid()
        self.image_grid.setFixedHeight(210)
        img_layout.addWidget(self.image_grid)
        self.image_grid.itemSelectionChanged.connect(self._on_image_selected)
        root.addWidget(img_group)

        self.selected_label = QLabel("Click an image to select it as the starting frame")
        self.selected_label.setObjectName("subtitle")
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.selected_label)

        # ── Segment progress ──────────────────────────────────────────────
        seg_group = QGroupBox("Segment Progress")
        seg_layout = QVBoxLayout(seg_group)

        dots_row = QHBoxLayout()
        dots_row.setSpacing(12)
        dots_row.addStretch()
        for i in range(1, 8):
            dot = SegmentDot(i)
            self._seg_dots.append(dot)
            dots_row.addWidget(dot)
            if i < 7:
                sep = QLabel("——")
                sep.setStyleSheet(f"color:{COLORS['fg_dim']};")
                dots_row.addWidget(sep)
        dots_row.addStretch()
        seg_layout.addLayout(dots_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 7)
        self.progress_bar.setValue(0)
        seg_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("subtitle")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        seg_layout.addWidget(self.progress_label)

        # Segment timing row — mirrors dots row exactly
        self._seg_time_labels: list[QLabel] = []
        times_row = QHBoxLayout()
        times_row.setSpacing(8)
        times_row.addStretch()
        for i in range(1, 8):
            time_lbl = QLabel("—")
            time_lbl.setFixedWidth(70)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_lbl.setStyleSheet(
                f"color:{COLORS['fg_secondary']}; font-size:8pt; font-family:Consolas;"
            )
            self._seg_time_labels.append(time_lbl)
            times_row.addWidget(time_lbl)
            if i < 7:
                gap = QLabel()
                gap.setFixedWidth(10)
                times_row.addWidget(gap)
        times_row.addStretch()
        seg_layout.addLayout(times_row)

        root.addWidget(seg_group)

        # ── Log ───────────────────────────────────────────────────────────
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(80)
        self.log_list.setSpacing(0)
        self.log_list.setUniformItemSizes(True)
        log_layout.addWidget(self.log_list)
        root.addWidget(log_group, stretch=1)

        # ── Status + buttons ──────────────────────────────────────────────
        self.final_label = QLabel("")
        self.final_label.setObjectName("final_label")
        self.final_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.final_label.setWordWrap(True)
        root.addWidget(self.final_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("▶  Start Chain")
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.start_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    # Image picker
    # ------------------------------------------------------------------ #

    def _populate_images(self):
        input_dir = Path(self.config.get("input_dir", ""))
        self.image_grid.load_images(input_dir)
        count = self.image_grid.count()
        if count == 0:
            self.selected_label.setText("No images found in input folder")
        else:
            self.selected_label.setText("Click an image to select it as the starting frame")

    def _on_mode_changed(self):
        mode = "local" if self._local_radio.isChecked() else "runpod"
        self.config.set("mode", mode)
        self.config.save()

    def _browse_final_dir(self):
        current = self.final_dir_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Final Video Folder", current or str(Path.home()))
        if folder:
            self.final_dir_edit.setText(folder)
            self.config.set("final_video_dir", folder)
            self.config.save()

    def _browse_zip(self):
        current = self.zip_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Archive Folder", current or str(Path.home()))
        if folder:
            self.zip_edit.setText(folder)
            self.config.set("zip_output_dir", folder)
            self.config.save()

    def _on_image_selected(self):
        name = self.image_grid.selected_image()
        if name:
            self.selected_label.setText(f"Selected: {name}")

    # ------------------------------------------------------------------ #
    # Chain start / cancel
    # ------------------------------------------------------------------ #

    def _start(self):
        image_name = self.image_grid.selected_image()
        if not image_name:
            QMessageBox.critical(self, "Error", "Please click an image to select it as the starting image.")
            return

        self.config.set("mode", "local" if self._local_radio.isChecked() else "runpod")
        self.config.set("runpod_url", self._runpod_url_edit.text().strip())
        self.config.set("final_video_dir", self.final_dir_edit.text().strip())
        self.config.set("zip_output_dir", self.zip_edit.text().strip())
        self.config.save()

        self._reset_ui()
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_label.setText("Starting...")
        self.final_label.setText("")

        self._worker = ChainWorker(self.config.get_all(), image_name)
        self._worker.log.connect(self._on_log)
        self._worker.segment_done.connect(self._on_segment_done)
        self._worker.segment_time.connect(self._on_segment_time)
        self._worker.stitch_done.connect(self._on_stitch_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

        self._seg_dots[0].set_active()
        self.progress_label.setText("Segment 1/7 — running...")

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Cancelling...")

    # ------------------------------------------------------------------ #
    # Worker signal handlers
    # ------------------------------------------------------------------ #

    def _on_log(self, message: str):
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def _on_segment_time(self, seg: int, elapsed: str):
        self._seg_time_labels[seg - 1].setText(elapsed)
        self._seg_time_labels[seg - 1].setStyleSheet(
            f"color:{COLORS['success']}; font-size:9pt; font-family:Consolas; font-weight:bold;"
        )

    def _on_segment_done(self, seg: int):
        self._seg_dots[seg - 1].set_done()
        self.progress_bar.setValue(seg)
        if seg < 7:
            self._seg_dots[seg].set_active()
            self.progress_label.setText(f"Segment {seg + 1}/7 — running...")
        else:
            self.progress_label.setText("Stitching final video...")

    def _on_stitch_done(self, final_path: str):
        self.final_label.setText(f"Final video saved: {final_path}")
        self.progress_label.setText("Complete!")
        self.progress_bar.setValue(7)
        dlg = CompletionDialog(final_path, parent=self)
        dlg.exec()

    def _on_error(self, message: str):
        self.progress_label.setText("Error")
        QMessageBox.critical(self, "Error", message)

    def _on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _reset_ui(self):
        for dot in self._seg_dots:
            dot.set_pending()
        for lbl in self._seg_time_labels:
            lbl.setText("—")
            lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:9pt; font-family:Consolas;")
        self.progress_bar.setValue(0)
        self.log_list.clear()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()
