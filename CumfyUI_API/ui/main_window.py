from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QProgressBar, QListWidget, QListWidgetItem, QGroupBox,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QAbstractItemView, QFileDialog,
)

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QImage

from config import ConfigManager
from worker import ChainWorker
from ui.styles import STYLESHEET, COLORS
from ui.video_player import VideoPlayerDialog
from ui.settings_dialog import SettingsDialog

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
THUMB_SIZE = 200
MAX_SEGMENTS = 10


class ImageLoaderThread(QThread):
    """Loads and scales images in the background; emits one item at a time."""
    image_ready = pyqtSignal(QImage, str, str)  # image, rel_path, label
    progress = pyqtSignal(int, int)             # current, total
    finished_loading = pyqtSignal(int)          # total loaded

    def __init__(self, input_dir: Path):
        super().__init__()
        self._input_dir = input_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        images = sorted(
            p for p in self._input_dir.rglob("*")
            if p.suffix.lower() in IMAGE_EXTS
        )
        total = len(images)
        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            img = QImage(str(img_path))
            if img.isNull():
                continue
            # Scale keeping aspect ratio into THUMB_SIZE box
            img = img.scaled(THUMB_SIZE, THUMB_SIZE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            rel = img_path.relative_to(self._input_dir)
            label = str(rel) if rel.parent != Path(".") else img_path.name
            self.image_ready.emit(img, str(rel), label)
            loaded += 1
            self.progress.emit(loaded, total)
        self.finished_loading.emit(loaded)


class CompletionDialog(QDialog):
    def __init__(self, final_path: str, seg_count: int, parent=None):
        super().__init__(parent)
        self._final_path = final_path
        self.setWindowTitle("Chain Complete!")
        self.setMinimumWidth(520)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(30, 30, 30, 30)

        icon = QLabel("✅")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 36pt;")
        layout.addWidget(icon)

        title = QLabel(f"All {seg_count} segments complete!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #4caf8a;")
        layout.addWidget(title)

        path_label = QLabel(final_path)
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("font-size: 12pt; color: #9090cc;")
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


class ImageGrid(QListWidget):
    """Scrollable thumbnail grid for picking the starting image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 12, THUMB_SIZE + 12))
        self.setSpacing(4)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWrapping(True)
        self.setWordWrap(False)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px;"
            f" padding-right: 16px; }}"
            f"QListWidget::item {{ border: 2px solid transparent; border-radius: 4px; }}"
            f"QListWidget::item:selected {{ background-color: transparent;"
            f" border: 2px solid {COLORS['accent']}; border-radius: 4px; }}"
        )

    def clear_grid(self):
        self.clear()

    def add_image(self, img: QImage, rel_path: str, label: str):
        pix = QPixmap.fromImage(img)
        canvas = QPixmap(THUMB_SIZE, THUMB_SIZE)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        x = (THUMB_SIZE - pix.width()) // 2
        y = (THUMB_SIZE - pix.height()) // 2
        painter.drawPixmap(x, y, pix)
        painter.end()
        item = QListWidgetItem(QIcon(canvas), label)
        item.setData(Qt.ItemDataRole.UserRole, rel_path)
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
        self._loader: ImageLoaderThread | None = None
        self._seg_dots: list[SegmentDot] = []
        self._seg_time_labels: list[QLabel] = []

        self.setWindowTitle(f"ComfyUI Chain Automator  v{version}")
        self.setMinimumSize(1200, 720)
        self.resize(1600, 760)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._populate_images()

    @property
    def _seg_count(self) -> int:
        workflows = self.config.get("workflows", [])
        return min(max(len(workflows), 1), MAX_SEGMENTS)

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header = QLabel("ComfyUI Workflow Chain Automator")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_light']};
                color: {COLORS['fg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 16pt;
                padding: 0px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent']}; color: white; }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        header_row.addStretch()
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(settings_btn)
        root.addLayout(header_row)

        # ── Split: left = image picker, right = controls ──────────────────
        split = QHBoxLayout()
        split.setSpacing(12)
        root.addLayout(split, stretch=1)

        # Left panel — image folder + grid
        left = QVBoxLayout()
        left.setSpacing(6)

        folder_row = QHBoxLayout()
        folder_lbl = QLabel("Image Folder:")
        folder_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._input_dir_edit = QLineEdit(self.config.get("input_dir", ""))
        self._input_dir_edit.setPlaceholderText("Folder containing starting images...")
        self._input_dir_edit.setReadOnly(True)
        folder_browse_btn = QPushButton("...")
        folder_browse_btn.setFixedWidth(40)
        folder_browse_btn.setFixedHeight(30)
        folder_browse_btn.clicked.connect(self._browse_input_dir)
        folder_row.addWidget(folder_lbl)
        folder_row.addWidget(self._input_dir_edit, stretch=1)
        folder_row.addWidget(folder_browse_btn)
        left.addLayout(folder_row)

        img_group = QGroupBox("Starting Image  (Segment 1) — click to select")
        img_layout = QVBoxLayout(img_group)
        img_layout.setContentsMargins(6, 6, 6, 6)
        self.image_grid = ImageGrid()
        img_layout.addWidget(self.image_grid)
        self.image_grid.itemSelectionChanged.connect(self._on_image_selected)
        left.addWidget(img_group, stretch=1)

        self.selected_label = QLabel("Click an image to select it as the starting frame")
        self.selected_label.setObjectName("subtitle")
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.selected_label)

        split.addLayout(left, stretch=3)

        # Right panel — progress + log + buttons
        right = QVBoxLayout()
        right.setSpacing(8)

        # Segment progress group — dots/timers built dynamically
        self._seg_group = QGroupBox("Segment Progress")
        self._seg_layout = QVBoxLayout(self._seg_group)
        self._rebuild_seg_panel()
        right.addWidget(self._seg_group)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setSpacing(-1)
        self.log_list.setUniformItemSizes(True)
        log_layout.addWidget(self.log_list)
        right.addWidget(log_group, stretch=1)

        # Status + buttons
        self.final_label = QLabel("")
        self.final_label.setObjectName("final_label")
        self.final_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.final_label.setWordWrap(True)
        right.addWidget(self.final_label)

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
        right.addLayout(btn_row)

        split.addLayout(right, stretch=2)

    def _rebuild_seg_panel(self):
        """Clear and rebuild dots/progress/timers based on current workflow count."""
        # Remove all existing widgets from seg_layout
        while self._seg_layout.count():
            item = self._seg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # clear child layout items
                child = item.layout()
                while child.count():
                    c = child.takeAt(0)
                    if c.widget():
                        c.widget().deleteLater()

        self._seg_dots = []
        self._seg_time_labels = []
        n = self._seg_count

        dots_row = QHBoxLayout()
        dots_row.setSpacing(6)
        dots_row.addStretch()
        for i in range(1, n + 1):
            dot = SegmentDot(i)
            self._seg_dots.append(dot)
            dots_row.addWidget(dot)
            if i < n:
                sep = QLabel("—")
                sep.setStyleSheet(f"color:{COLORS['fg_dim']};")
                dots_row.addWidget(sep)
        dots_row.addStretch()
        self._seg_layout.addLayout(dots_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, n)
        self.progress_bar.setValue(0)
        self._seg_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("subtitle")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._seg_layout.addWidget(self.progress_label)

        times_row = QHBoxLayout()
        times_row.setSpacing(4)
        times_row.addStretch()
        for i in range(1, n + 1):
            time_lbl = QLabel("[m:s]")
            time_lbl.setFixedWidth(55)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_lbl.setStyleSheet(
                f"color:{COLORS['fg_secondary']}; font-size:8pt; font-family:Consolas;"
            )
            self._seg_time_labels.append(time_lbl)
            times_row.addWidget(time_lbl)
            if i < n:
                gap = QLabel()
                gap.setFixedWidth(3)
                times_row.addWidget(gap)
        times_row.addStretch()
        self._seg_layout.addLayout(times_row)

    # ------------------------------------------------------------------ #
    # Image picker
    # ------------------------------------------------------------------ #

    def _populate_images(self):
        input_dir = Path(self._input_dir_edit.text().strip() or self.config.get("input_dir", ""))

        # Cancel any existing loader
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait()

        self.image_grid.clear_grid()
        self.selected_label.setText("Loading images...")
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # indeterminate spinner until total is known
        self.progress_label.setText("Loading images...")
        self.start_btn.setEnabled(False)

        if not input_dir.exists():
            self.selected_label.setText("No images found in input folder")
            self.progress_bar.setRange(0, self._seg_count)
            self.progress_label.setText("Ready")
            self.start_btn.setEnabled(True)
            return

        self._loader = ImageLoaderThread(input_dir)
        self._loader.image_ready.connect(self.image_grid.add_image)
        self._loader.progress.connect(self._on_load_progress)
        self._loader.finished_loading.connect(self._on_load_finished)
        self._loader.start()

    def _on_load_progress(self, current: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Loading images... {current}/{total}")

    def _on_load_finished(self, total: int):
        self.progress_bar.setRange(0, self._seg_count)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Ready")
        self.start_btn.setEnabled(True)
        if total == 0:
            self.selected_label.setText("No images found in input folder")
        else:
            self.selected_label.setText("Click an image to select it as the starting frame")

    def _browse_input_dir(self):
        current = self._input_dir_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", current or str(Path.home()))
        if folder:
            self._input_dir_edit.setText(folder)
            self.config.set("input_dir", folder)
            self.config.save()
            self._populate_images()

    def _open_settings(self):
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec():
            self._rebuild_seg_panel()
            self._populate_images()

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
        self.progress_label.setText(f"Segment 1/{self._seg_count} — running...")

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
        if seg - 1 < len(self._seg_time_labels):
            self._seg_time_labels[seg - 1].setText(elapsed)
            self._seg_time_labels[seg - 1].setStyleSheet(
                f"color:{COLORS['success']}; font-size:10pt; font-family:Consolas; font-weight:bold;"
            )

    def _on_segment_done(self, seg: int):
        n = self._seg_count
        if seg - 1 < len(self._seg_dots):
            self._seg_dots[seg - 1].set_done()
        self.progress_bar.setValue(seg)
        if seg < n:
            if seg < len(self._seg_dots):
                self._seg_dots[seg].set_active()
            self.progress_label.setText(f"Segment {seg + 1}/{n} — running...")
        else:
            self.progress_label.setText("Stitching final video...")

    def _on_stitch_done(self, final_path: str):
        self.final_label.setText(f"Final video saved: {final_path}")
        self.progress_label.setText("Complete!")
        self.progress_bar.setValue(self._seg_count)
        dlg = CompletionDialog(final_path, self._seg_count, parent=self)
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
            lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:8pt; font-family:Arial;")
        self.progress_bar.setValue(0)
        self.log_list.clear()

    def closeEvent(self, event):
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait(3000)
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()
