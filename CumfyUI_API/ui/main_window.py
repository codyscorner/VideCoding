from datetime import datetime
from pathlib import Path
import subprocess
import threading

from PIL import Image, ImageOps

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QProgressBar, QListWidget, QListWidgetItem, QGroupBox,
    QVBoxLayout, QHBoxLayout, QStackedWidget,
    QDialog, QMessageBox, QAbstractItemView, QFileDialog, QCheckBox, QComboBox,
    QProgressDialog,
)

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QImage

from config import ConfigManager
from batch_worker import BatchChainWorker
from ui.styles import STYLESHEET, COLORS
from ui.video_player import VideoPlayerDialog
from ui.settings_dialog import SettingsDialog
from ui.segment_editor import SegmentEditorDialog
from ui.generate_tab import GenerateTab
from ui.widgets import ThumbnailGrid, THUMB_SIZE

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}
MAX_SEGMENTS = 10


# ------------------------------------------------------------------ #
# Background loaders
# ------------------------------------------------------------------ #

class ImageLoaderThread(QThread):
    image_ready = pyqtSignal(QImage, str, str)
    progress = pyqtSignal(int, int)
    finished_loading = pyqtSignal(int)

    def __init__(self, input_dir: Path, excluded_stems: set[str] | None = None):
        super().__init__()
        self._input_dir = input_dir
        self._excluded_stems = excluded_stems or set()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        all_images = sorted(
            p for p in self._input_dir.rglob("*")
            if p.suffix.lower() in IMAGE_EXTS
        )
        images = [p for p in all_images if p.stem not in self._excluded_stems]
        total = len(images)
        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            try:
                pil_img = Image.open(img_path)
                pil_img = ImageOps.exif_transpose(pil_img)
                pil_img = pil_img.convert("RGBA")
                data = pil_img.tobytes("raw", "RGBA")
                img = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            except Exception:
                img = QImage(str(img_path))
            if img.isNull():
                continue
            img = img.scaled(THUMB_SIZE, THUMB_SIZE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            rel = img_path.relative_to(self._input_dir)
            label = str(rel) if rel.parent != Path(".") else img_path.name
            self.image_ready.emit(img, str(rel), label)
            loaded += 1
            self.progress.emit(loaded, total)
        self.finished_loading.emit(loaded)


class VideoLoaderThread(QThread):
    """Loads video thumbnails from cache; generates missing ones via FFmpeg."""
    video_ready = pyqtSignal(QImage, str, str)  # image, full_path, label
    progress = pyqtSignal(int, int)              # current, total (thumbnail generation)
    thumbnails_needed = pyqtSignal(int)          # fires with count before generation starts
    finished_loading = pyqtSignal(int)

    def __init__(self, video_dir: Path, ffmpeg: str, sort_key=None, sort_reverse: bool = False):
        super().__init__()
        self._video_dir = video_dir
        self._ffmpeg = ffmpeg
        self._sort_key = sort_key or (lambda p: p.name.lower())
        self._sort_reverse = sort_reverse
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        thumb_dir = self._video_dir / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        videos = sorted(
            (p for p in self._video_dir.iterdir() if p.suffix.lower() in VIDEO_EXTS),
            key=self._sort_key,
            reverse=self._sort_reverse,
        )

        # Phase 1: generate any missing thumbnails
        missing = [
            (v, thumb_dir / (v.stem + ".jpg"))
            for v in videos
            if not (thumb_dir / (v.stem + ".jpg")).exists()
        ]
        if missing:
            self.thumbnails_needed.emit(len(missing))
            for i, (vid_path, thumb_path) in enumerate(missing, 1):
                if self._cancelled:
                    return
                self._extract_frame(vid_path, thumb_path)
                self.progress.emit(i, len(missing))

        # Phase 2: load all into grid
        loaded = 0
        for vid_path in videos:
            if self._cancelled:
                return
            thumb_path = thumb_dir / (vid_path.stem + ".jpg")
            img = QImage(str(thumb_path))
            if img.isNull():
                continue
            img = img.scaled(THUMB_SIZE, THUMB_SIZE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            self.video_ready.emit(img, str(vid_path), vid_path.name)
            loaded += 1
        self.finished_loading.emit(loaded)

    def _extract_frame(self, vid_path: Path, thumb_path: Path):
        try:
            subprocess.run(
                [self._ffmpeg, "-y", "-i", str(vid_path),
                 "-vframes", "1", "-q:v", "3", str(thumb_path)],
                capture_output=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass


# ------------------------------------------------------------------ #
# Completion dialog
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# Segment dot
# ------------------------------------------------------------------ #

class SegmentDot(QLabel):
    double_clicked = pyqtSignal(int)

    def __init__(self, number: int):
        super().__init__(f" {number} ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(34, 34)
        self.setToolTip("Double-click to edit workflow")
        self._number = number
        self.set_pending()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self._number)

    def _apply(self, bg: str, fg: str):
        self.setStyleSheet(
            f"background-color:{bg}; color:{fg}; border-radius:17px;"
            f" font-weight:bold; font-size:10pt;"
        )

    def set_pending(self): self._apply(COLORS['seg_pending'], COLORS['fg_dim'])
    def set_active(self):  self._apply(COLORS['seg_active'], '#000000')
    def set_done(self):    self._apply(COLORS['seg_done'], '#000000')


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    _VID_SORT_OPTIONS = [
        ("Newest First",   lambda p: p.stat().st_mtime, True),
        ("Oldest First",   lambda p: p.stat().st_mtime, False),
        ("Name A → Z",     lambda p: p.name.lower(),    False),
        ("Name Z → A",     lambda p: p.name.lower(),    True),
        ("Largest First",  lambda p: p.stat().st_size,  True),
        ("Smallest First", lambda p: p.stat().st_size,  False),
    ]

    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version
        self._worker: BatchChainWorker | None = None
        self._img_loader: ImageLoaderThread | None = None
        self._vid_loader: VideoLoaderThread | None = None
        self._last_vid_dir: str = ""
        self._seg_dots: list[SegmentDot] = []
        self._seg_time_labels: list[QLabel] = []

        self.setWindowTitle(f"ComfyUI Chain Automator  v{version}")
        self.setMinimumSize(1200, 780)
        self.resize(1600, 860)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._refresh_chain_folders()
        self._populate_images()

    @property
    def _seg_count(self) -> int:
        folder = self.config.get("active_chain_folder", "")
        wf_dir = Path(self.config.get("workflow_dir", ""))
        if folder and wf_dir:
            chain_dir = wf_dir / folder
            if chain_dir.exists():
                return min(len(list(chain_dir.glob("workflow_segment_*_batch.json"))), MAX_SEGMENTS)
            return 0
        return min(max(len(self.config.get("workflows", [])), 1), MAX_SEGMENTS)

    def _ffmpeg_path(self) -> str:
        return self.config.get("ffmpeg_path", "ffmpeg") or "ffmpeg"

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

        # Mode toggle buttons
        mode_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['bg_light']};
                color: {COLORS['fg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
                padding: 4px 16px;
                min-width: 90px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['accent']};
                color: white;
                border: 1px solid {COLORS['accent']};
            }}
            QPushButton:hover:!checked {{ background-color: {COLORS['bg_medium']}; }}
        """
        self._chain_btn = QPushButton("⛓  Chain")
        self._chain_btn.setCheckable(True)
        self._chain_btn.setChecked(True)
        self._chain_btn.setFixedHeight(32)
        self._chain_btn.setStyleSheet(mode_btn_style)
        self._chain_btn.clicked.connect(lambda: self._switch_view(0))

        self._library_btn = QPushButton("🎬  Library")
        self._library_btn.setCheckable(True)
        self._library_btn.setChecked(False)
        self._library_btn.setFixedHeight(32)
        self._library_btn.setStyleSheet(mode_btn_style)
        self._library_btn.clicked.connect(lambda: self._switch_view(1))

        self._generate_btn = QPushButton("✨  Generate")
        self._generate_btn.setCheckable(True)
        self._generate_btn.setChecked(False)
        self._generate_btn.setFixedHeight(32)
        self._generate_btn.setStyleSheet(mode_btn_style)
        self._generate_btn.clicked.connect(lambda: self._switch_view(2))

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

        header_row.addWidget(self._chain_btn)
        header_row.addSpacing(4)
        header_row.addWidget(self._library_btn)
        header_row.addSpacing(4)
        header_row.addWidget(self._generate_btn)
        header_row.addStretch()
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(settings_btn)
        root.addLayout(header_row)

        # ── Stacked pages ─────────────────────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._build_chain_page())
        self._stack.addWidget(self._build_library_page())
        self._generate_tab = GenerateTab(self.config, parent=self)
        self._generate_tab.send_to_chain.connect(self._on_send_to_chain)
        self._generate_tab.start_one_shot.connect(self._on_start_one_shot)
        self._stack.addWidget(self._generate_tab)

    def _build_chain_page(self) -> QWidget:
        page = QWidget()
        split = QHBoxLayout(page)
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(12)

        # Left — image picker
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
        self._show_all_chk = QCheckBox("Show all")
        self._show_all_chk.setToolTip("Include images that already have a video in the library")
        self._show_all_chk.setChecked(False)
        self._show_all_chk.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._show_all_chk.stateChanged.connect(lambda _: self._populate_images())
        folder_row.addWidget(folder_lbl)
        folder_row.addWidget(self._input_dir_edit, stretch=1)
        folder_row.addWidget(folder_browse_btn)
        folder_row.addSpacing(8)
        folder_row.addWidget(self._show_all_chk)
        left.addLayout(folder_row)

        self._img_group = QGroupBox("Starting Images — Ctrl+click or Shift+click to select multiple")
        img_layout = QVBoxLayout(self._img_group)
        img_layout.setContentsMargins(6, 6, 6, 6)
        self.image_grid = ThumbnailGrid()
        self.image_grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        img_layout.addWidget(self.image_grid)
        self.image_grid.itemSelectionChanged.connect(self._on_image_selected)
        left.addWidget(self._img_group, stretch=1)

        self.selected_label = QLabel("Select images to include in the batch")
        self.selected_label.setObjectName("subtitle")
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.selected_label)

        split.addLayout(left, stretch=3)

        # Right — progress + log + buttons
        right = QVBoxLayout()
        right.setSpacing(8)

        # ── Chain selector ────────────────────────────────────────────────
        chain_sel_row = QHBoxLayout()
        chain_sel_lbl = QLabel("Chain:")
        chain_sel_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        chain_sel_lbl.setFixedWidth(48)
        self._chain_folder_combo = QComboBox()
        self._chain_folder_combo.setMinimumHeight(30)
        self._chain_folder_combo.setToolTip("Select a video chain workflow folder")
        self._chain_folder_combo.currentIndexChanged.connect(self._on_chain_folder_changed)
        refresh_chain_btn = QPushButton("↻")
        refresh_chain_btn.setFixedSize(30, 30)
        refresh_chain_btn.setToolTip("Refresh chain folder list")
        refresh_chain_btn.clicked.connect(self._refresh_chain_folders)
        chain_sel_row.addWidget(chain_sel_lbl)
        chain_sel_row.addWidget(self._chain_folder_combo, stretch=1)
        chain_sel_row.addWidget(refresh_chain_btn)
        right.addLayout(chain_sel_row)

        self._seg_group = QGroupBox("Segment Progress")
        self._seg_layout = QVBoxLayout(self._seg_group)
        self._rebuild_seg_panel()
        right.addWidget(self._seg_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setSpacing(-1)
        self.log_list.setUniformItemSizes(True)
        log_layout.addWidget(self.log_list)
        right.addWidget(log_group, stretch=1)

        self.final_label = QLabel("")
        self.final_label.setObjectName("final_label")
        self.final_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.final_label.setWordWrap(True)
        right.addWidget(self.final_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("▶  Start Batch")
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
        return page

    def _build_library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar row
        toolbar = QHBoxLayout()
        vid_folder_lbl = QLabel("Video Folder:")
        vid_folder_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._vid_dir_edit = QLineEdit(self.config.get("final_video_dir", ""))
        self._vid_dir_edit.setPlaceholderText("Folder containing video files...")
        self._vid_dir_edit.setReadOnly(True)
        vid_browse_btn = QPushButton("...")
        vid_browse_btn.setFixedWidth(40)
        vid_browse_btn.setFixedHeight(40)
        vid_browse_btn.clicked.connect(self._browse_video_dir)
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedHeight(40)
        refresh_btn.clicked.connect(lambda: self._populate_videos(force=True))
        self._vid_sort_combo = QComboBox()
        self._vid_sort_combo.setFixedHeight(40)
        self._vid_sort_combo.setMinimumWidth(160)
        for label, *_ in self._VID_SORT_OPTIONS:
            self._vid_sort_combo.addItem(label)
        self._vid_sort_combo.currentIndexChanged.connect(self._on_vid_sort_changed)
        self._vid_delete_btn = QPushButton("🗑  Delete")
        self._vid_delete_btn.setFixedHeight(40)
        self._vid_delete_btn.setObjectName("cancel_btn")
        self._vid_delete_btn.setEnabled(False)
        self._vid_delete_btn.clicked.connect(self._delete_selected_video)
        toolbar.addWidget(vid_folder_lbl)
        toolbar.addWidget(self._vid_dir_edit, stretch=1)
        toolbar.addWidget(vid_browse_btn)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._vid_sort_combo)
        toolbar.addSpacing(4)
        toolbar.addWidget(refresh_btn)
        toolbar.addSpacing(4)
        toolbar.addWidget(self._vid_delete_btn)
        layout.addLayout(toolbar)

        # Video grid
        vid_group = QGroupBox("Videos — double-click to play")
        vid_layout = QVBoxLayout(vid_group)
        vid_layout.setContentsMargins(6, 6, 6, 6)
        self.video_grid = ThumbnailGrid()
        self.video_grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.video_grid.itemDoubleClicked.connect(self._on_video_double_clicked)
        self.video_grid.itemSelectionChanged.connect(
            lambda: self._vid_delete_btn.setEnabled(bool(self.video_grid.selected_keys()))
        )
        vid_layout.addWidget(self.video_grid)
        layout.addWidget(vid_group, stretch=1)

        # Status bar
        lib_bottom = QHBoxLayout()
        self._vid_status_label = QLabel("Select a video folder to browse")
        self._vid_status_label.setObjectName("subtitle")
        self._vid_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vid_progress = QProgressBar()
        self._vid_progress.setRange(0, 1)
        self._vid_progress.setValue(0)
        self._vid_progress.setFixedHeight(16)
        self._vid_progress.setVisible(False)
        lib_bottom.addWidget(self._vid_status_label, stretch=1)
        lib_bottom.addWidget(self._vid_progress)
        layout.addLayout(lib_bottom)

        return page

    def _switch_view(self, index: int):
        self._chain_btn.setChecked(index == 0)
        self._library_btn.setChecked(index == 1)
        self._generate_btn.setChecked(index == 2)
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._populate_videos()
        elif index == 2:
            self._generate_tab.refresh_mode()

    # ------------------------------------------------------------------ #
    # Segment panel
    # ------------------------------------------------------------------ #

    def _rebuild_seg_panel(self):
        while self._seg_layout.count():
            item = self._seg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                child = item.layout()
                while child.count():
                    c = child.takeAt(0)
                    if c.widget():
                        c.widget().deleteLater()

        self._seg_dots = []
        self._seg_time_labels = []
        n = self._seg_count

        if n == 0:
            no_wf_label = QLabel("No *_batch.json workflow files found in selected folder")
            no_wf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_wf_label.setStyleSheet(f"color:{COLORS['fg_dim']}; font-size:10pt;")
            self._seg_layout.addWidget(no_wf_label)
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self._seg_layout.addWidget(self.progress_bar)
            self.progress_label = QLabel("No workflows configured")
            self.progress_label.setObjectName("subtitle")
            self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._seg_layout.addWidget(self.progress_label)
            return

        dots_row = QHBoxLayout()
        dots_row.setSpacing(6)
        dots_row.addStretch()
        for i in range(1, n + 1):
            dot = SegmentDot(i)
            dot.double_clicked.connect(self._on_seg_dot_double_clicked)
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
    # Image picker (Chain view)
    # ------------------------------------------------------------------ #

    def _existing_video_stems(self) -> set[str]:
        """Return stems of videos in the final video folder.
        Adds both the raw stem and the _N-stripped stem so images like
        'photo_1.png' are excluded when 'photo_1.mp4' exists, and plain
        'photo.png' is excluded when 'photo_1.mp4' (auto-numbered) exists."""
        import re
        vid_dir = Path(self.config.get("final_video_dir", ""))
        if not vid_dir.exists():
            return set()
        stems: set[str] = set()
        for p in vid_dir.iterdir():
            if p.suffix.lower() in VIDEO_EXTS:
                stems.add(p.stem)
                stems.add(re.sub(r'_\d+$', '', p.stem))
        return stems

    def _populate_images(self):
        input_dir = Path(self._input_dir_edit.text().strip() or self.config.get("input_dir", ""))

        if self._img_loader and self._img_loader.isRunning():
            self._img_loader.cancel()
            self._img_loader.wait()

        self.image_grid.clear_grid()
        self.selected_label.setText("Loading images...")
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("Loading images...")
        self.start_btn.setEnabled(False)

        if not input_dir.exists():
            self.selected_label.setText("No images found in input folder")
            self.progress_bar.setRange(0, self._seg_count)
            self.progress_label.setText("Ready")
            self.start_btn.setEnabled(True)
            return

        # Warn if any stem appears with more than one extension
        stem_exts: dict[str, list[str]] = {}
        for p in input_dir.rglob("*"):
            if p.suffix.lower() in IMAGE_EXTS:
                stem_exts.setdefault(p.stem, []).append(p.suffix.lower())
        duplicates = {s: exts for s, exts in stem_exts.items() if len(exts) > 1}
        if duplicates:
            lines = "\n".join(
                f"  {s}: {', '.join(exts)}" for s, exts in list(duplicates.items())[:10]
            )
            QMessageBox.warning(
                self, "Duplicate Filenames Detected",
                f"Some files share the same name but have different extensions:\n\n{lines}\n\n"
                "Consider converting your batch folder to a single extension (e.g. all PNG) "
                "to avoid ambiguous one-to-one matching."
            )

        if self._show_all_chk.isChecked():
            excluded = set()
        else:
            excluded = self._existing_video_stems()

        self._img_loader = ImageLoaderThread(input_dir, excluded)
        self._img_loader.image_ready.connect(self.image_grid.add_item)
        self._img_loader.progress.connect(self._on_img_load_progress)
        self._img_loader.finished_loading.connect(self._on_img_load_finished)
        self._img_loader.start()

    def _on_img_load_progress(self, current: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Loading images... {current}/{total}")

    def _on_img_load_finished(self, total: int):
        self.progress_bar.setRange(0, self._seg_count)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Ready")
        self.start_btn.setEnabled(True)
        self.image_grid.sort_by_filename()
        if total == 0:
            self.selected_label.setText("No images found in input folder")
        else:
            self.selected_label.setText("Select images to include in the batch")

    def _browse_input_dir(self):
        current = self._input_dir_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", current or str(Path.home()))
        if folder:
            self._input_dir_edit.setText(folder)
            self.config.set("input_dir", folder)
            self.config.save()
            self._populate_images()

    def _on_image_selected(self):
        keys = self.image_grid.selected_keys()
        if not keys:
            return
        self.selected_label.setText(
            f"{len(keys)} image{'s' if len(keys) > 1 else ''} selected"
        )

    # ------------------------------------------------------------------ #
    # Video library (Library view)
    # ------------------------------------------------------------------ #

    def _populate_videos(self, force: bool = False):
        vid_dir = Path(self._vid_dir_edit.text().strip() or self.config.get("final_video_dir", ""))

        # Skip reload if same folder already loaded
        if not force and str(vid_dir) == self._last_vid_dir and self.video_grid.count() > 0:
            return

        if self._vid_loader and self._vid_loader.isRunning():
            self._vid_loader.cancel()
            self._vid_loader.wait()

        self._last_vid_dir = str(vid_dir)
        self.video_grid.clear_grid()
        self._vid_progress.setVisible(True)
        self._vid_progress.setRange(0, 0)
        self._vid_status_label.setText("Loading videos...")

        if not vid_dir.exists():
            self._vid_status_label.setText("Video folder not found — check Settings")
            self._vid_progress.setVisible(False)
            return

        self._thumb_gen_dlg: QProgressDialog | None = None
        sort_idx = self._vid_sort_combo.currentIndex()
        _, sort_key, sort_reverse = self._VID_SORT_OPTIONS[sort_idx]
        self._vid_loader = VideoLoaderThread(vid_dir, self._ffmpeg_path(), sort_key, sort_reverse)
        self._vid_loader.video_ready.connect(self.video_grid.add_item)
        self._vid_loader.thumbnails_needed.connect(self._on_thumbnails_needed)
        self._vid_loader.progress.connect(self._on_vid_load_progress)
        self._vid_loader.finished_loading.connect(self._on_vid_load_finished)
        self._vid_loader.start()

    def _on_thumbnails_needed(self, count: int):
        self._thumb_gen_dlg = QProgressDialog(
            f"Generating {count} new thumbnail{'s' if count != 1 else ''}...",
            None, 0, count, self
        )
        self._thumb_gen_dlg.setWindowTitle("Updating Library")
        self._thumb_gen_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self._thumb_gen_dlg.setMinimumWidth(380)
        self._thumb_gen_dlg.setAutoClose(False)
        self._thumb_gen_dlg.setAutoReset(False)
        self._thumb_gen_dlg.setValue(0)
        self._thumb_gen_dlg.show()

    def _on_vid_load_progress(self, current: int, total: int):
        if self._thumb_gen_dlg and self._thumb_gen_dlg.isVisible():
            self._thumb_gen_dlg.setLabelText(f"Generating thumbnails... {current}/{total}")
            self._thumb_gen_dlg.setValue(current)
        else:
            self._vid_progress.setRange(0, total)
            self._vid_progress.setValue(current)
            self._vid_status_label.setText(f"Loading thumbnails... {current}/{total}")

    def _on_vid_load_finished(self, total: int):
        if self._thumb_gen_dlg:
            self._thumb_gen_dlg.close()
            self._thumb_gen_dlg = None
        self._vid_progress.setVisible(False)
        if total == 0:
            self._vid_status_label.setText("No video files found in folder")
        else:
            self._vid_status_label.setText(f"{total} video{'s' if total != 1 else ''} — double-click to play")

    def _on_vid_sort_changed(self):
        self._populate_videos(force=True)

    def _browse_video_dir(self):
        current = self._vid_dir_edit.text().strip()
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder", current or str(Path.home()))
        if folder:
            self._vid_dir_edit.setText(folder)
            self.config.set("final_video_dir", folder)
            self.config.save()
            self._populate_videos()

    def _on_video_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            player = VideoPlayerDialog(path, parent=self)
            player.exec()

    def _delete_selected_video(self):
        keys = self.video_grid.selected_keys()
        if not keys:
            return
        n = len(keys)
        if n == 1:
            msg = f"Permanently delete:\n{Path(keys[0]).name}?\n\nThis cannot be undone."
        else:
            msg = f"Permanently delete {n} videos?\n\nThis cannot be undone."
        reply = QMessageBox.question(
            self, "Delete Video", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for key in keys:
            path = Path(key)
            try:
                path.unlink()
                (path.parent / "thumbnails" / (path.stem + ".jpg")).unlink(missing_ok=True)
            except OSError as e:
                errors.append(f"{path.name}: {e}")
        if errors:
            QMessageBox.critical(self, "Error", "Some files could not be deleted:\n" + "\n".join(errors))
        for item in self.video_grid.selectedItems():
            self.video_grid.takeItem(self.video_grid.row(item))
        self._vid_delete_btn.setEnabled(False)
        count = self.video_grid.count()
        self._vid_status_label.setText(
            f"{count} video{'s' if count != 1 else ''} — double-click to play"
            if count > 0 else "No video files found in folder"
        )

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    def _refresh_chain_folders(self):
        wf_dir = Path(self.config.get("workflow_dir", ""))
        self._chain_folder_combo.blockSignals(True)
        self._chain_folder_combo.clear()
        if wf_dir.exists():
            folders = sorted(
                p.name for p in wf_dir.iterdir()
                if p.is_dir()
            )
            for f in folders:
                self._chain_folder_combo.addItem(f)
        last = self.config.get("active_chain_folder", "")
        if last:
            idx = self._chain_folder_combo.findText(last)
            if idx >= 0:
                self._chain_folder_combo.setCurrentIndex(idx)
        self._chain_folder_combo.blockSignals(False)
        # Always persist whatever folder is currently shown so the worker sees it
        current = self._chain_folder_combo.currentText()
        if current:
            self.config.set("active_chain_folder", current)
            self.config.save()
        # Rebuild segment panel to reflect the now-selected folder
        self._rebuild_seg_panel()

    def _on_chain_folder_changed(self, _idx: int):
        folder = self._chain_folder_combo.currentText()
        self.config.set("active_chain_folder", folder)
        self.config.save()
        self._rebuild_seg_panel()

    def _on_seg_dot_double_clicked(self, segment: int):
        workflow_dir = Path(self.config.get("workflow_dir", ""))
        folder = self.config.get("active_chain_folder", "")
        if folder:
            seg_file = f"workflow_segment_{segment:02d}_batch.json"
            json_path = workflow_dir / folder / seg_file
        else:
            workflows = self.config.get("workflows", [])
            wf = next((w for w in workflows if w["segment"] == segment), None)
            if not wf:
                return
            json_path = workflow_dir / wf["json_file"]
        dlg = SegmentEditorDialog(segment, json_path, config=self.config, parent=self)
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec():
            self._refresh_chain_folders()
            self._populate_images()
            self._vid_dir_edit.setText(self.config.get("final_video_dir", ""))
            self._generate_tab.refresh_mode()
            self._generate_tab.refresh_workflows()

    # ------------------------------------------------------------------ #
    # Generate tab signal handlers
    # ------------------------------------------------------------------ #

    def _inject_generated_image(self, path: str):
        """Add a generated image into the chain grid and select it."""
        input_dir = Path(self._input_dir_edit.text().strip() or self.config.get("input_dir", ""))
        img_path = Path(path)
        try:
            key = str(img_path.relative_to(input_dir))
        except ValueError:
            key = img_path.name

        # If already in grid, just select it
        self.image_grid.select_key(key)
        if self.image_grid.selected_key() == key:
            self.selected_label.setText(f"Selected: {key}")
            return

        # Load thumbnail and add to grid
        img = QImage(path)
        if img.isNull():
            return
        img = img.scaled(
            THUMB_SIZE, THUMB_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_grid.add_item(img, key, img_path.name)
        self.image_grid.select_key(key)
        self.selected_label.setText(f"Selected: {key}")

    def _on_send_to_chain(self, path: str):
        self._inject_generated_image(path)
        self._switch_view(0)

    def _on_start_one_shot(self, path: str):
        self._inject_generated_image(path)
        self._switch_view(0)
        self._start()

    # ------------------------------------------------------------------ #
    # Chain start / cancel
    # ------------------------------------------------------------------ #

    def _start(self):
        self.config.save()
        self.final_label.setText("")

        keys = self.image_grid.selected_keys()
        if not keys:
            QMessageBox.critical(self, "Error", "Select at least one image for the batch.")
            return
        self._reset_ui()
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_label.setText(f"Batch: {len(keys)} images — Starting...")
        self._worker = BatchChainWorker(self.config.get_all(), keys)
        self._worker.log.connect(self._on_log)
        self._worker.segment_done.connect(self._on_segment_done)
        self._worker.segment_time.connect(self._on_segment_time)
        self._worker.all_done.connect(self._on_batch_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        self._seg_dots[0].set_active()
        self.progress_label.setText(f"Batch: {len(keys)} images — Segment 1/{self._seg_count}...")

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText("Cancelling...")

    # ------------------------------------------------------------------ #
    # Worker signal handlers
    # ------------------------------------------------------------------ #

    def _on_log(self, message: str):
        self.log_list.addItem(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
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
            self.progress_label.setText(f"Batch — Segment {seg + 1}/{n} — running...")
        else:
            self.progress_label.setText("Stitching all videos...")

    def _on_stitch_done(self, final_path: str):
        self._play_completion_sound()
        self.final_label.setText(f"Final video saved: {final_path}")
        self.progress_label.setText("Complete!")
        self.progress_bar.setValue(self._seg_count)
        dlg = CompletionDialog(final_path, self._seg_count, parent=self)
        dlg.exec()
        if not self._show_all_chk.isChecked():
            self._populate_images()

    def _play_completion_sound(self):
        if not self.config.get("completion_sound_enabled", False):
            return
        path = self.config.get("completion_sound_path", "").strip()
        if not path:
            return
        sound_path = Path(path)
        if not sound_path.exists():
            return

        def _do_play():
            try:
                if sound_path.suffix.lower() == ".wav":
                    import winsound
                    winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
                else:
                    import os
                    os.startfile(str(sound_path))
            except Exception:
                pass

        threading.Thread(target=_do_play, daemon=True).start()

    def _on_batch_done(self, final_paths: list):
        self._play_completion_sound()
        n = len(final_paths)
        self.progress_label.setText(f"Batch complete — {n} video{'s' if n != 1 else ''}")
        self.final_label.setText(f"{n} videos saved to final video folder")

        if not self._show_all_chk.isChecked():
            processed_stems = {Path(p).stem for p in final_paths}
            self.image_grid.remove_items_by_stems(processed_stems)

        msg = "\n".join(Path(p).name for p in final_paths)
        reply = QMessageBox.question(
            self, "Batch Complete",
            f"Generated {n} video{'s' if n != 1 else ''}:\n\n{msg}\n\nPlay all videos now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            seen: set[str] = set()
            existing = []
            for p in final_paths:
                if Path(p).exists() and p not in seen:
                    existing.append(p)
                    seen.add(p)
            if existing:
                player = VideoPlayerDialog(existing[0], parent=self, playlist=existing)
                player.exec()
        if not self._show_all_chk.isChecked():
            self._populate_images()

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
        for loader in (self._img_loader, self._vid_loader):
            if loader and loader.isRunning():
                loader.cancel()
                loader.wait(3000)
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        self.config.set("input_dir", self._input_dir_edit.text().strip())
        self.config.set("active_chain_folder", self._chain_folder_combo.currentText())
        self.config.save()
        event.accept()
