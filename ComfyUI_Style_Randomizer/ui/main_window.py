import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import Qt, QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QImage, QColor, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QProgressBar, QListWidget, QListWidgetItem, QGroupBox,
    QVBoxLayout, QHBoxLayout, QSplitter, QStackedWidget,
    QFileDialog, QAbstractItemView, QPlainTextEdit, QCheckBox,
    QStatusBar, QComboBox, QMessageBox, QDialog, QSizePolicy,
    QSpinBox,
)

import csv

from config import ConfigManager
from worker import (
    BatchStyleWorker, load_prompts, log_prompt_used, PromptEntry,
    IMAGE_EXTS, OUTPUT_EXTS, PROMPT_LOG_NAME,
)
from ui.styles import COLORS
from ui.settings_dialog import SettingsDialog
from ui.prompt_editor import PromptEditorDialog
from ui.pin_dialog import PinPromptDialog

THUMB_SIZE = 120

SORT_OPTIONS = [
    ("Newest First",   lambda p: p.stat().st_mtime, True),
    ("Oldest First",   lambda p: p.stat().st_mtime, False),
    ("Name A → Z",     lambda p: p.name.lower(),    False),
    ("Name Z → A",     lambda p: p.name.lower(),    True),
    ("Largest First",  lambda p: p.stat().st_size,  True),
    ("Smallest First", lambda p: p.stat().st_size,  False),
]

_MODE_BTN_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_light']};
        color: {COLORS['fg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        font-size: 10pt;
        font-weight: bold;
        padding: 4px 18px;
        min-width: 100px;
    }}
    QPushButton:checked {{
        background-color: {COLORS['accent']};
        color: white;
        border: 1px solid {COLORS['accent']};
    }}
    QPushButton:hover:!checked {{ background-color: {COLORS['bg_medium']}; }}
"""


# ------------------------------------------------------------------ #
# Background image loaders
# ------------------------------------------------------------------ #

class ImageLoaderThread(QThread):
    image_ready       = pyqtSignal(QImage, str, str, bool)  # img, key, label, is_processed
    thumbnails_needed = pyqtSignal(int)                      # count before generation starts
    gen_progress      = pyqtSignal(int, int)                 # current, total (generation phase)
    progress          = pyqtSignal(int, int)                 # loaded, total (loading phase)
    finished_loading  = pyqtSignal(int)

    def __init__(self, input_dir: Path, processed_stems: set | None = None, show_all: bool = False):
        super().__init__()
        self._input_dir = input_dir
        self._processed_stems = processed_stems or set()
        self._show_all = show_all
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            all_images = sorted(
                (p for p in self._input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS),
                key=lambda p: p.name.lower(),
            )
        except OSError:
            self.finished_loading.emit(0)
            return

        thumb_dir = self._input_dir / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        # Phase 1: generate missing thumbnails for all images in folder
        missing = [
            (p, thumb_dir / (p.stem + ".jpg"))
            for p in all_images
            if not (thumb_dir / (p.stem + ".jpg")).exists()
        ]
        if missing:
            self.thumbnails_needed.emit(len(missing))
            for i, (img_path, thumb_path) in enumerate(missing, 1):
                if self._cancelled:
                    return
                self._generate_thumb(img_path, thumb_path)
                self.gen_progress.emit(i, len(missing))

        # Phase 2: load filtered set from cache
        images = [
            p for p in all_images
            if self._show_all or p.stem not in self._processed_stems
        ]
        total  = len(images)
        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            is_processed = img_path.stem in self._processed_stems
            thumb_path = thumb_dir / (img_path.stem + ".jpg")
            img = QImage(str(thumb_path))
            if img.isNull():
                try:
                    pil = Image.open(img_path)
                    pil = ImageOps.exif_transpose(pil).convert("RGBA")
                    data = pil.tobytes("raw", "RGBA")
                    img = QImage(data, pil.width, pil.height, QImage.Format.Format_RGBA8888)
                except Exception:
                    img = QImage(str(img_path))
            if img.isNull():
                continue
            img = img.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_ready.emit(img, str(img_path), img_path.name, is_processed)
            loaded += 1
            self.progress.emit(loaded, total)

        self.finished_loading.emit(loaded)

    def _generate_thumb(self, img_path: Path, thumb_path: Path):
        try:
            pil = Image.open(img_path)
            pil = ImageOps.exif_transpose(pil).convert("RGB")
            pil.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
            pil.save(thumb_path, "JPEG", quality=85)
        except Exception:
            pass


class LibraryLoaderThread(QThread):
    image_ready       = pyqtSignal(QImage, str, str)
    progress          = pyqtSignal(int, int)  # current, total (generation phase)
    thumbnails_needed = pyqtSignal(int)        # count before generation starts
    finished_loading  = pyqtSignal(int)

    def __init__(self, output_dir: Path, sort_idx: int = 0):
        super().__init__()
        self._output_dir = output_dir
        _, self._sort_key, self._sort_reverse = SORT_OPTIONS[sort_idx]
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            images = sorted(
                (p for p in self._output_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS),
                key=self._sort_key,
                reverse=self._sort_reverse,
            )
        except OSError:
            self.finished_loading.emit(0)
            return

        thumb_dir = self._output_dir / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        # Phase 1: generate missing thumbnails
        missing = [
            (p, thumb_dir / (p.stem + ".jpg"))
            for p in images
            if not (thumb_dir / (p.stem + ".jpg")).exists()
        ]
        if missing:
            self.thumbnails_needed.emit(len(missing))
            for i, (img_path, thumb_path) in enumerate(missing, 1):
                if self._cancelled:
                    return
                self._generate_thumb(img_path, thumb_path)
                self.progress.emit(i, len(missing))

        # Phase 2: load all from cache
        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            thumb_path = thumb_dir / (img_path.stem + ".jpg")
            img = QImage(str(thumb_path))
            if img.isNull():
                # fallback: decode source image directly
                try:
                    pil = Image.open(img_path)
                    pil = ImageOps.exif_transpose(pil).convert("RGBA")
                    data = pil.tobytes("raw", "RGBA")
                    img = QImage(data, pil.width, pil.height, QImage.Format.Format_RGBA8888)
                except Exception:
                    img = QImage(str(img_path))
            if img.isNull():
                continue
            img = img.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_ready.emit(img, str(img_path), img_path.name)
            loaded += 1

        self.finished_loading.emit(loaded)

    def _generate_thumb(self, img_path: Path, thumb_path: Path):
        try:
            pil = Image.open(img_path)
            pil = ImageOps.exif_transpose(pil).convert("RGB")
            pil.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
            pil.save(thumb_path, "JPEG", quality=85)
        except Exception:
            pass


# ------------------------------------------------------------------ #
# Full-size image viewer dialog
# ------------------------------------------------------------------ #

class ImageViewerDialog(QDialog):
    _SLIDE_MS = 4000

    def __init__(self, paths: list[str], index: int = 0, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._index = index
        self._orig_pix: QPixmap | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(self._SLIDE_MS)
        self._timer.timeout.connect(self._slideshow_tick)
        self.setWindowTitle("Image Viewer")
        self.setMinimumSize(960, 720)
        self.resize(1100, 800)
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._title_lbl = QLabel()
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setObjectName("subtitle")
        layout.addWidget(self._title_lbl)

        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._img_lbl.setMinimumSize(200, 200)
        layout.addWidget(self._img_lbl, stretch=1)

        _BTN_H = 42

        nav_row = QHBoxLayout()
        self._prev_btn = QPushButton("←  Prev")
        self._prev_btn.setMinimumWidth(130)
        self._prev_btn.setFixedHeight(_BTN_H)
        self._prev_btn.clicked.connect(self._prev)

        self._next_btn = QPushButton("Next  →")
        self._next_btn.setMinimumWidth(130)
        self._next_btn.setFixedHeight(_BTN_H)
        self._next_btn.clicked.connect(self._next)

        self._play_btn = QPushButton("▶  Slideshow")
        self._play_btn.setMinimumWidth(160)
        self._play_btn.setFixedHeight(_BTN_H)
        self._play_btn.setToolTip("Auto-advance every 4s full-screen  (Space = skip ahead,  Esc = stop)")
        self._play_btn.clicked.connect(self._toggle_slideshow)

        self._fs_btn = QPushButton("⛶  Full Screen")
        self._fs_btn.setMinimumWidth(170)
        self._fs_btn.setFixedHeight(_BTN_H)
        self._fs_btn.clicked.connect(self._toggle_fullscreen)

        close_btn = QPushButton("✕  Close")
        close_btn.setObjectName("cancel_btn")
        close_btn.setMinimumWidth(110)
        close_btn.setFixedHeight(_BTN_H)
        close_btn.clicked.connect(self.accept)

        nav_row.addWidget(self._prev_btn)
        nav_row.addWidget(self._next_btn)
        nav_row.addStretch()
        nav_row.addWidget(self._play_btn)
        nav_row.addSpacing(8)
        nav_row.addWidget(self._fs_btn)
        nav_row.addStretch()
        nav_row.addWidget(close_btn)
        layout.addLayout(nav_row)

    def _load_current(self):
        path = self._paths[self._index]
        name = Path(path).name
        self._title_lbl.setText(f"{name}  ({self._index + 1} / {len(self._paths)})")
        self.setWindowTitle(f"Image Viewer — {name}")
        self._prev_btn.setEnabled(self._index > 0)
        self._next_btn.setEnabled(self._index < len(self._paths) - 1)
        self._orig_pix = QPixmap(path)
        self._update_display()

    def _update_display(self):
        if self._orig_pix and not self._orig_pix.isNull():
            scaled = self._orig_pix.scaled(
                self._img_lbl.width(),
                self._img_lbl.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._img_lbl.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._load_current()

    def _next(self):
        if self._index < len(self._paths) - 1:
            self._index += 1
            self._load_current()

    # ------------------------------------------------------------------ #
    # Full screen
    # ------------------------------------------------------------------ #

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self._fs_btn.setText("⛶  Full Screen")
        else:
            self.showFullScreen()
            self._fs_btn.setText("↙  Exit Full Screen")

    # ------------------------------------------------------------------ #
    # Slideshow
    # ------------------------------------------------------------------ #

    def _toggle_slideshow(self):
        if self._timer.isActive():
            self._stop_slideshow()
        else:
            self._start_slideshow()

    def _start_slideshow(self):
        if not self.isFullScreen():
            self.showFullScreen()
            self._fs_btn.setText("↙  Exit Full Screen")
        self._play_btn.setText("⏹  Stop")
        self._timer.start()

    def _stop_slideshow(self):
        self._timer.stop()
        self._play_btn.setText("▶  Slideshow")

    def _slideshow_tick(self):
        if self._index < len(self._paths) - 1:
            self._next()
        else:
            self._timer.stop()
            self._show_end_slide()
            QTimer.singleShot(3000, self._stop_slideshow)

    def _show_end_slide(self):
        self._title_lbl.setText("End of Slideshow")
        w = max(self._img_lbl.width(), 400)
        h = max(self._img_lbl.height(), 300)
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.black)
        painter = QPainter(pix)
        painter.setPen(QColor(200, 200, 200))
        f = QFont("Arial", 36, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "✓   End of Slideshow")
        painter.end()
        self._img_lbl.setPixmap(pix)

    # ------------------------------------------------------------------ #
    # Keyboard
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        elif key == Qt.Key.Key_Space:
            if self._timer.isActive():
                # Skip ahead immediately and reset the 4s countdown
                self._timer.stop()
                if self._index < len(self._paths) - 1:
                    self._next()
                    self._timer.start()
                else:
                    self._show_end_slide()
                    QTimer.singleShot(3000, self._stop_slideshow)
        elif key == Qt.Key.Key_Escape:
            if self._timer.isActive():
                self._stop_slideshow()
            elif self.isFullScreen():
                self.showNormal()
                self._fs_btn.setText("⛶  Full Screen")
            else:
                self.accept()
        elif key == Qt.Key.Key_Return:
            self.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ------------------------------------------------------------------ #
# Thumbnail grid
# ------------------------------------------------------------------ #

class ThumbnailGrid(QListWidget):
    def __init__(self, parent=None, selection_mode=QAbstractItemView.SelectionMode.NoSelection):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 12, THUMB_SIZE + 28))
        self.setSpacing(4)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(selection_mode)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px; }}"
            f"QListWidget::item {{ border: 1px solid transparent; border-radius: 3px; }}"
            f"QListWidget::item:selected {{ border: 2px solid {COLORS['accent']}; "
            f"background-color: rgba(94,75,219,0.25); }}"
        )

    def add_item(self, img: QImage, key: str, label: str, is_processed: bool = False,
                 is_pinned: bool = False):
        pix    = QPixmap.fromImage(img)
        canvas = QPixmap(THUMB_SIZE, THUMB_SIZE)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        painter.drawPixmap((THUMB_SIZE - pix.width()) // 2,
                           (THUMB_SIZE - pix.height()) // 2, pix)
        if is_pinned:
            badge = 24
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(230, 150, 20, 235))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(3, 3, badge, badge)
            painter.setPen(QColor(255, 255, 255))
            f = QFont("Arial", 12, QFont.Weight.Bold)
            painter.setFont(f)
            painter.drawText(3, 3, badge, badge, Qt.AlignmentFlag.AlignCenter, "📌")
        if is_processed:
            badge = 26
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(30, 190, 60, 230))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(THUMB_SIZE - badge - 3, 3, badge, badge)
            painter.setPen(QColor(255, 255, 255))
            f = QFont("Arial", 13, QFont.Weight.Bold)
            painter.setFont(f)
            painter.drawText(
                THUMB_SIZE - badge - 3, 3, badge, badge,
                Qt.AlignmentFlag.AlignCenter, "✓"
            )
        painter.end()
        item = QListWidgetItem(QIcon(canvas), label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.addItem(item)

    def all_paths(self) -> list[Path]:
        return [Path(self.item(i).data(Qt.ItemDataRole.UserRole))
                for i in range(self.count())]

    def selected_keys(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.selectedItems()]

    def remove_items_by_stems(self, stems: set[str]):
        for i in range(self.count() - 1, -1, -1):
            item = self.item(i)
            key = item.data(Qt.ItemDataRole.UserRole) if item else None
            if key and Path(key).stem in stems:
                self.takeItem(i)


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, base_dir: Path, version: str = ""):
        super().__init__()
        self._config   = config
        self._base_dir = base_dir
        self._version  = version
        self._prompts: list[PromptEntry] = []
        self._pinned: dict[str, str] = {}  # image stem -> pinned prompt text
        self._worker: BatchStyleWorker | None = None
        self._loader: ImageLoaderThread | None = None
        self._lib_loader: LibraryLoaderThread | None = None
        self._last_lib_dir: str = ""
        self._reroll_worker: BatchStyleWorker | None = None
        self._processed_count: int = 0
        self._auto_mode = False
        self._auto_stop_requested = False
        self._auto_current_batch: list[Path] = []
        self._last_auto_prompt_idx: int = -1
        self._auto_prompt_cursor: int = 0  # cursor for sequential/evens_odds auto mode

        self._build_ui()
        self._load_initial_state()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        title = f"ComfyUI Style Randomizer v{self._version}" if self._version else "ComfyUI Style Randomizer"
        self.setWindowTitle(title)
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # Header with view toggle buttons
        hdr_row = QHBoxLayout()
        self._randomizer_btn = QPushButton("🎲  Randomizer")
        self._randomizer_btn.setCheckable(True)
        self._randomizer_btn.setChecked(True)
        self._randomizer_btn.setFixedHeight(32)
        self._randomizer_btn.setStyleSheet(_MODE_BTN_STYLE)
        self._randomizer_btn.clicked.connect(lambda: self._switch_view(0))

        self._library_btn = QPushButton("🖼  Library")
        self._library_btn.setCheckable(True)
        self._library_btn.setChecked(False)
        self._library_btn.setFixedHeight(32)
        self._library_btn.setStyleSheet(_MODE_BTN_STYLE)
        self._library_btn.clicked.connect(lambda: self._switch_view(1))

        hdr_row.addWidget(self._randomizer_btn)
        hdr_row.addSpacing(4)
        hdr_row.addWidget(self._library_btn)
        hdr_row.addStretch()

        hdr_lbl = QLabel("ComfyUI Style Randomizer")
        hdr_lbl.setObjectName("header")
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()

        self._mode_lbl = QLabel("● Local")
        self._mode_lbl.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        hdr_row.addWidget(self._mode_lbl)
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("small_btn")
        settings_btn.setFixedWidth(100)
        settings_btn.clicked.connect(self._open_settings)
        hdr_row.addWidget(settings_btn)
        root.addLayout(hdr_row)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_main_page())
        self._stack.addWidget(self._build_library_page())
        root.addWidget(self._stack, stretch=1)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._update_status()

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Input folder row
        input_row = QHBoxLayout()
        input_lbl = QLabel("Input Folder:")
        input_lbl.setFixedWidth(100)
        input_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._input_edit = QLineEdit()
        self._input_edit.setText(self._config.get("input_dir", ""))
        self._input_edit.setPlaceholderText("Folder containing source images…")
        self._input_edit.editingFinished.connect(self._on_input_edited)
        input_browse = QPushButton("Browse")
        input_browse.setObjectName("small_btn")
        input_browse.setFixedWidth(70)
        input_browse.clicked.connect(self._browse_input)
        self._img_count_lbl = QLabel("Images: 0")
        self._img_count_lbl.setObjectName("subtitle")
        self._show_all_chk = QCheckBox("Show all")
        self._show_all_chk.setToolTip("Include already-processed images (shown with ✓ badge)")
        self._show_all_chk.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._show_all_chk.setChecked(False)
        self._show_all_chk.stateChanged.connect(self._on_show_all_changed)
        input_row.addWidget(input_lbl)
        input_row.addWidget(self._input_edit, stretch=1)
        input_row.addWidget(input_browse)
        input_row.addSpacing(10)
        input_row.addWidget(self._img_count_lbl)
        input_row.addSpacing(10)
        input_row.addWidget(self._show_all_chk)
        layout.addLayout(input_row)

        # Splitter: thumbnails | prompts+log
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_w = QWidget()
        left_v = QVBoxLayout(left_w)
        left_v.setContentsMargins(0, 0, 0, 0)
        self._thumb_grid = ThumbnailGrid()
        self._thumb_grid.itemDoubleClicked.connect(self._on_thumb_double_clicked)
        self._thumb_grid.setToolTip("Double-click an image to pin a specific style to it")
        left_v.addWidget(self._thumb_grid)
        splitter.addWidget(left_w)

        right_w = QWidget()
        right_v = QVBoxLayout(right_w)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(6)

        prompt_group = QGroupBox("Style Prompts")
        pg_v = QVBoxLayout(prompt_group)
        prompt_hdr = QHBoxLayout()
        self._prompt_count_lbl = QLabel("0 prompts loaded")
        self._prompt_count_lbl.setObjectName("subtitle")
        edit_prompts_btn = QPushButton("Edit Prompts")
        edit_prompts_btn.setObjectName("small_btn")
        edit_prompts_btn.setFixedWidth(100)
        edit_prompts_btn.clicked.connect(self._open_prompt_editor)
        prompt_hdr.addWidget(self._prompt_count_lbl)
        prompt_hdr.addStretch()
        prompt_hdr.addWidget(edit_prompts_btn)
        pg_v.addLayout(prompt_hdr)
        self._prompt_list = QListWidget()
        self._prompt_list.setMaximumHeight(190)
        pg_v.addWidget(self._prompt_list)
        right_v.addWidget(prompt_group)

        log_group = QGroupBox("Processing Log")
        lg_v = QVBoxLayout(log_group)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        lg_v.addWidget(self._log_view)
        right_v.addWidget(log_group, stretch=1)

        splitter.addWidget(right_w)
        splitter.setSizes([620, 430])
        layout.addWidget(splitter, stretch=1)

        # Bottom — progress + controls
        bottom_row = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setFormat("%v / %m")
        self._progress.setValue(0)
        bottom_row.addWidget(self._progress, stretch=1)

        order_lbl = QLabel("Order:")
        order_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        bottom_row.addWidget(order_lbl)
        self._prompt_order_combo = QComboBox()
        self._prompt_order_combo.addItem("Evens → Odds", "evens_odds")
        self._prompt_order_combo.addItem("Random",      "random")
        self._prompt_order_combo.addItem("Sequential",  "sequential")
        self._prompt_order_combo.setFixedHeight(28)
        self._prompt_order_combo.setFixedWidth(130)
        self._prompt_order_combo.setToolTip(
            "Evens → Odds: even-numbered styles first, then odd\n"
            "Random: each image gets a random style\n"
            "Sequential: styles assigned in order (1, 2, 3…)"
        )
        bottom_row.addWidget(self._prompt_order_combo)
        bottom_row.addSpacing(8)

        self._start_btn = QPushButton("Start")
        self._start_btn.setMinimumWidth(100)
        self._start_btn.clicked.connect(lambda: self._start())
        bottom_row.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setMinimumWidth(100)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        bottom_row.addWidget(self._cancel_btn)

        layout.addLayout(bottom_row)

        # Auto run row
        auto_row = QHBoxLayout()
        auto_row.addStretch()
        auto_lbl = QLabel("Batch size:")
        auto_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._auto_size_spin = QSpinBox()
        self._auto_size_spin.setRange(1, 50)
        self._auto_size_spin.setValue(4)
        self._auto_size_spin.setFixedHeight(28)
        self._auto_size_spin.setFixedWidth(64)
        self._auto_size_spin.setToolTip("Images per auto batch (1–50)")
        _auto_btn_style = "font-size: 9pt; padding: 4px 14px;"
        self._auto_btn = QPushButton("▶▶  Auto Run")
        self._auto_btn.setFixedHeight(28)
        self._auto_btn.setStyleSheet(
            f"QPushButton {{ background-color: #4a78d4; color: white;"
            f" border-radius: 4px; font-weight: bold; {_auto_btn_style} }}"
            f"QPushButton:hover {{ background-color: #5b8ce0; }}"
            f"QPushButton:disabled {{ background-color: {COLORS['bg_light']};"
            f" color: {COLORS['fg_dim']}; {_auto_btn_style} }}"
        )
        self._auto_btn.setToolTip("Automatically process all images N at a time, no prompts between batches")
        self._auto_btn.clicked.connect(self._start_auto)
        self._stop_auto_btn = QPushButton("⏹  Stop After Batch")
        self._stop_auto_btn.setObjectName("cancel_btn")
        self._stop_auto_btn.setFixedHeight(28)
        self._stop_auto_btn.setStyleSheet(f"QPushButton {{ font-size: 9pt; padding: 4px 14px; }}")
        self._stop_auto_btn.setEnabled(False)
        self._stop_auto_btn.setToolTip("Finish the current batch then stop auto mode")
        self._stop_auto_btn.clicked.connect(self._stop_auto_after_batch)
        auto_row.addWidget(auto_lbl)
        auto_row.addSpacing(4)
        auto_row.addWidget(self._auto_size_spin)
        auto_row.addSpacing(10)
        auto_row.addWidget(self._auto_btn)
        auto_row.addSpacing(8)
        auto_row.addWidget(self._stop_auto_btn)
        auto_row.addStretch()
        layout.addLayout(auto_row)

        return page

    def _build_library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        folder_lbl = QLabel("Output Folder:")
        folder_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._lib_folder_lbl = QLabel("—")
        self._lib_folder_lbl.setStyleSheet(f"color:{COLORS['fg_dim']}; font-size:9pt;")
        self._lib_folder_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._lib_sort_combo = QComboBox()
        self._lib_sort_combo.setFixedHeight(36)
        self._lib_sort_combo.setMinimumWidth(150)
        for label, *_ in SORT_OPTIONS:
            self._lib_sort_combo.addItem(label)
        self._lib_sort_combo.currentIndexChanged.connect(lambda _: self._populate_library(force=True))

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(lambda: self._populate_library(force=True))

        self._lib_view_btn = QPushButton("👁  View")
        self._lib_view_btn.setFixedHeight(36)
        self._lib_view_btn.setEnabled(False)
        self._lib_view_btn.clicked.connect(self._view_selected)

        self._lib_reroll_btn = QPushButton("🎲  Re-roll")
        self._lib_reroll_btn.setFixedHeight(36)
        self._lib_reroll_btn.setEnabled(False)
        self._lib_reroll_btn.setToolTip("Re-process this image with a new random style (source must still be in the input folder)")
        self._lib_reroll_btn.clicked.connect(self._reroll_selected)

        self._lib_delete_btn = QPushButton("🗑  Delete")
        self._lib_delete_btn.setObjectName("cancel_btn")
        self._lib_delete_btn.setFixedHeight(36)
        self._lib_delete_btn.setEnabled(False)
        self._lib_delete_btn.clicked.connect(self._delete_selected)

        toolbar.addWidget(folder_lbl)
        toolbar.addWidget(self._lib_folder_lbl, stretch=1)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._lib_sort_combo)
        toolbar.addSpacing(4)
        toolbar.addWidget(refresh_btn)
        toolbar.addSpacing(4)
        toolbar.addWidget(self._lib_view_btn)
        toolbar.addSpacing(4)
        toolbar.addWidget(self._lib_reroll_btn)
        toolbar.addSpacing(4)
        toolbar.addWidget(self._lib_delete_btn)
        layout.addLayout(toolbar)

        # Grid
        lib_group = QGroupBox(
            "Output Images — double-click to view  |  Ctrl+click or Shift+click for multi-select"
        )
        lg_v = QVBoxLayout(lib_group)
        lg_v.setContentsMargins(6, 6, 6, 6)
        self._lib_grid = ThumbnailGrid(
            selection_mode=QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._lib_grid.itemDoubleClicked.connect(self._on_lib_double_clicked)
        self._lib_grid.itemSelectionChanged.connect(self._on_lib_selection_changed)
        lg_v.addWidget(self._lib_grid)
        layout.addWidget(lib_group, stretch=1)

        # Progress bar (thumbnail generation)
        self._lib_progress = QProgressBar()
        self._lib_progress.setFixedHeight(6)
        self._lib_progress.setTextVisible(False)
        self._lib_progress.setValue(0)
        self._lib_progress.hide()
        layout.addWidget(self._lib_progress)

        # Status
        self._lib_status_lbl = QLabel("Switch to the Randomizer tab to set an output folder")
        self._lib_status_lbl.setObjectName("subtitle")
        self._lib_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lib_status_lbl)

        return page

    # ------------------------------------------------------------------ #
    # View switching
    # ------------------------------------------------------------------ #

    def _switch_view(self, index: int):
        self._randomizer_btn.setChecked(index == 0)
        self._library_btn.setChecked(index == 1)
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._populate_library()

    # ------------------------------------------------------------------ #
    # Path handling
    # ------------------------------------------------------------------ #

    def _browse_input(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Folder", self._input_edit.text())
        if path:
            self._input_edit.setText(path)
            self._on_input_edited()

    def _on_input_edited(self):
        self._config.set("input_dir", self._input_edit.text())
        self._config.save()
        self._reload_images()

    # ------------------------------------------------------------------ #
    # Data loading — main tab
    # ------------------------------------------------------------------ #

    def _load_initial_state(self):
        self._reload_images()
        self._reload_prompts()
        self._update_mode_label()
        self._update_status()
        self._update_auto_buttons()

    def _on_show_all_changed(self):
        self._reload_images()
        self._update_auto_buttons()

    def _existing_output_stems(self) -> set:
        output_dir = Path(self._config.get("output_dir", ""))
        if not output_dir.is_dir():
            return set()
        return {p.stem for p in output_dir.iterdir() if p.suffix.lower() in OUTPUT_EXTS}

    def _reload_images(self):
        input_dir = Path(self._config.get("input_dir", ""))
        if not input_dir.is_dir():
            return
        if self._loader:
            self._loader.cancel()
            self._loader.wait()
        self._thumb_grid.clear()
        self._img_count_lbl.setText("Loading…")
        show_all = self._show_all_chk.isChecked()
        processed = self._existing_output_stems()
        self._processed_count = len(processed)
        self._loader = ImageLoaderThread(input_dir, processed_stems=processed, show_all=show_all)
        self._loader.image_ready.connect(
            lambda img, key, lbl, is_proc: self._thumb_grid.add_item(
                img, key, lbl, is_proc, Path(key).stem in self._pinned
            )
        )
        self._loader.thumbnails_needed.connect(self._on_img_thumbs_needed)
        self._loader.gen_progress.connect(self._on_img_gen_progress)
        self._loader.progress.connect(self._on_img_load_progress)
        self._loader.finished_loading.connect(self._on_images_loaded)
        self._loader.start()

    def _on_img_thumbs_needed(self, count: int):
        self._progress.setMaximum(count)
        self._progress.setValue(0)
        self._img_count_lbl.setText(f"Generating thumbnails… 0 / {count}")

    def _on_img_gen_progress(self, current: int, total: int):
        self._progress.setValue(current)
        self._img_count_lbl.setText(f"Generating thumbnails… {current} / {total}")

    def _on_img_load_progress(self, current: int, total: int):
        self._progress.setMaximum(total)
        self._progress.setValue(current)
        self._img_count_lbl.setText(f"Loading… {current} / {total}")

    def _on_images_loaded(self, count: int):
        self._progress.setValue(0)
        self._progress.setMaximum(max(count, 1))
        done = self._processed_count
        if done > 0:
            self._img_count_lbl.setText(f"Remaining: {count}  |  Done: {done}")
        else:
            self._img_count_lbl.setText(f"Remaining: {count}")

    def _reload_prompts(self):
        prompts_file = Path(self._config.get("prompts_file", ""))
        if not prompts_file.is_file():
            return
        try:
            self._prompts = load_prompts(prompts_file)
        except Exception:
            self._prompts = []
        self._refresh_prompt_list()

    def _refresh_prompt_list(self):
        self._prompt_list.clear()
        for i, entry in enumerate(self._prompts):
            preview = entry.text.replace("\n", " ")[:90]
            label = f"{i+1}.  {preview}"
            if entry.weight != 1.0:
                label += f"   [{entry.weight:g}x]"
            self._prompt_list.addItem(label)
        n = len(self._prompts)
        self._prompt_count_lbl.setText(f"{n} style prompt{'s' if n != 1 else ''} loaded")

    # ------------------------------------------------------------------ #
    # Per-image prompt pinning
    # ------------------------------------------------------------------ #

    def _on_thumb_double_clicked(self, item: QListWidgetItem):
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        stem = Path(key).stem
        if not self._prompts:
            self._append_log("No prompts loaded — configure a prompts file before pinning.")
            return
        dlg = PinPromptDialog(Path(key).name, self._prompts, self._pinned.get(stem), self)
        if dlg.exec() and dlg.chosen is not None:
            if dlg.chosen == "":
                self._pinned.pop(stem, None)
            else:
                self._pinned[stem] = dlg.chosen
            self._reload_images()

    # ------------------------------------------------------------------ #
    # Data loading — library tab
    # ------------------------------------------------------------------ #

    def _populate_library(self, force: bool = False):
        output_dir = Path(self._config.get("output_dir", ""))
        self._lib_folder_lbl.setText(str(output_dir) if output_dir != Path("") else "—")

        if not force and str(output_dir) == self._last_lib_dir and self._lib_grid.count() > 0:
            return

        if self._lib_loader and self._lib_loader.isRunning():
            self._lib_loader.cancel()
            self._lib_loader.wait()

        self._last_lib_dir = str(output_dir)
        self._lib_grid.clear()
        self._lib_view_btn.setEnabled(False)
        self._lib_delete_btn.setEnabled(False)

        if not output_dir.is_dir():
            self._lib_status_lbl.setText("Output folder not set or not found — configure it in the Randomizer tab")
            return

        self._lib_status_lbl.setText("Loading…")
        self._lib_progress.hide()
        self._lib_progress.setValue(0)
        sort_idx = self._lib_sort_combo.currentIndex()
        self._lib_loader = LibraryLoaderThread(output_dir, sort_idx)
        self._lib_loader.image_ready.connect(
            lambda img, key, lbl: self._lib_grid.add_item(img, key, lbl)
        )
        self._lib_loader.thumbnails_needed.connect(self._on_lib_thumbs_needed)
        self._lib_loader.progress.connect(self._on_lib_gen_progress)
        self._lib_loader.finished_loading.connect(self._on_lib_loaded)
        self._lib_loader.start()

    def _on_lib_thumbs_needed(self, count: int):
        self._lib_progress.setMaximum(count)
        self._lib_progress.setValue(0)
        self._lib_progress.show()
        self._lib_status_lbl.setText(f"Generating thumbnails… 0 / {count}")

    def _on_lib_gen_progress(self, current: int, total: int):
        self._lib_progress.setValue(current)
        self._lib_status_lbl.setText(f"Generating thumbnails… {current} / {total}")

    def _on_lib_loaded(self, count: int):
        self._lib_progress.hide()
        self._lib_progress.setValue(0)
        if count == 0:
            self._lib_status_lbl.setText("No images in output folder")
        else:
            self._lib_status_lbl.setText(
                f"{count} image{'s' if count != 1 else ''} — double-click to view"
            )

    def _on_lib_selection_changed(self):
        keys = self._lib_grid.selected_keys()
        has_sel = bool(keys)
        self._lib_view_btn.setEnabled(has_sel)
        self._lib_delete_btn.setEnabled(has_sel)
        self._lib_reroll_btn.setEnabled(len(keys) == 1 and self._worker is None)
        total = self._lib_grid.count()
        if has_sel:
            n = len(keys)
            self._lib_status_lbl.setText(f"{n} of {total} selected")
        elif total > 0:
            self._lib_status_lbl.setText(
                f"{total} image{'s' if total != 1 else ''} — double-click to view"
            )

    def _on_lib_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            all_paths = [
                self._lib_grid.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self._lib_grid.count())
            ]
            idx = all_paths.index(path) if path in all_paths else 0
            dlg = ImageViewerDialog(all_paths, idx, parent=self)
            dlg.exec()

    def _view_selected(self):
        keys = self._lib_grid.selected_keys()
        if not keys:
            return
        existing = [k for k in keys if Path(k).exists()]
        if not existing:
            return
        dlg = ImageViewerDialog(existing, 0, parent=self)
        dlg.exec()

    def _delete_selected(self):
        keys = self._lib_grid.selected_keys()
        if not keys:
            return
        n = len(keys)
        msg = (
            f"Permanently delete:\n{Path(keys[0]).name}?\n\nThis cannot be undone."
            if n == 1 else
            f"Permanently delete {n} images?\n\nThis cannot be undone."
        )
        reply = QMessageBox.question(
            self, "Delete Images", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for key in keys:
            try:
                p = Path(key)
                p.unlink()
                thumb = p.parent / "thumbnails" / (p.stem + ".jpg")
                if thumb.exists():
                    thumb.unlink()
            except OSError as e:
                errors.append(f"{Path(key).name}: {e}")
        if errors:
            QMessageBox.critical(self, "Error", "Some files could not be deleted:\n" + "\n".join(errors))
        for item in self._lib_grid.selectedItems():
            self._lib_grid.takeItem(self._lib_grid.row(item))
        self._lib_delete_btn.setEnabled(False)
        self._lib_view_btn.setEnabled(False)
        count = self._lib_grid.count()
        self._lib_status_lbl.setText(
            f"{count} image{'s' if count != 1 else ''} — double-click to view"
            if count > 0 else "No images in output folder"
        )

    # ------------------------------------------------------------------ #
    # Re-roll
    # ------------------------------------------------------------------ #

    def _last_prompt_index_for(self, image_name: str) -> int | None:
        output_dir = Path(self._config.get("output_dir", ""))
        log_path = output_dir / PROMPT_LOG_NAME
        if not log_path.is_file():
            return None
        last = None
        try:
            with open(log_path, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("image") == image_name:
                        last = row.get("prompt_index")
        except OSError:
            return None
        try:
            return int(last)
        except (TypeError, ValueError):
            return None

    def _reroll_selected(self):
        keys = self._lib_grid.selected_keys()
        if len(keys) != 1:
            return
        out_path = Path(keys[0])
        stem = out_path.stem
        input_dir = Path(self._config.get("input_dir", ""))
        source = next(
            (p for ext in IMAGE_EXTS if (p := input_dir / f"{stem}{ext}").is_file()),
            None,
        )
        if source is None:
            QMessageBox.warning(
                self, "Re-roll",
                f"Source image for '{out_path.name}' was not found in the input folder — cannot re-roll."
            )
            return
        if not self._prompts:
            QMessageBox.warning(self, "Re-roll", "No prompts loaded — configure a prompts file in Settings.")
            return

        reply = QMessageBox.question(
            self, "Re-roll",
            f"Re-process {out_path.name} with a new random style?\n\nThis will overwrite the current output.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        prev_idx = self._last_prompt_index_for(out_path.name)
        texts = [e.text for e in self._prompts]
        n = len(texts)
        if n == 1:
            idx = 0
        else:
            available = [i for i in range(n) if (i + 1) != prev_idx]
            weights = [self._prompts[i].weight for i in available]
            idx = random.choices(available, weights=weights, k=1)[0]
        new_prompt = texts[idx]

        reroll_config = self._config.get_all()
        reroll_config["skip_existing"] = False

        self._lib_reroll_btn.setEnabled(False)
        self._lib_delete_btn.setEnabled(False)
        self._lib_view_btn.setEnabled(False)
        self._lib_status_lbl.setText(f"Re-rolling {out_path.name}…")

        self._reroll_worker = BatchStyleWorker(
            config=reroll_config,
            prompts=self._prompts,
            image_paths=[source],
            fixed_prompt=new_prompt,
            prompt_mode="random",
            base_dir=self._base_dir,
        )
        self._reroll_worker.log.connect(self._append_log)
        self._reroll_worker.all_done.connect(self._on_reroll_done)
        self._reroll_worker.error.connect(self._on_reroll_error)
        self._reroll_worker.start()

    def _on_reroll_done(self):
        self._append_log("Re-roll complete.")
        self._reroll_worker = None
        self._populate_library(force=True)

    def _on_reroll_error(self, msg: str):
        self._append_log(f"Re-roll ERROR: {msg}")
        QMessageBox.critical(self, "Re-roll Error", msg)
        self._reroll_worker = None
        self._on_lib_selection_changed()

    # ------------------------------------------------------------------ #
    # Dialogs
    # ------------------------------------------------------------------ #

    def _open_prompt_editor(self):
        prompts_file = Path(self._config.get("prompts_file", ""))
        if not prompts_file.is_file():
            self._append_log("No prompts file set — configure it in ⚙ Settings.")
            return
        dlg = PromptEditorDialog(prompts_file, self._config, self)
        if dlg.exec():
            self._reload_prompts()

    def _open_settings(self):
        dlg = SettingsDialog(self._config, self)
        if dlg.exec():
            self._reload_prompts()
            self._update_mode_label()
            self._update_status()
            self._reload_images()  # output_dir may have changed; refresh processed stems

    # ------------------------------------------------------------------ #
    # Auto mode
    # ------------------------------------------------------------------ #

    def _get_next_auto_batch(self) -> list[Path]:
        count = self._thumb_grid.count()
        if count == 0:
            return []
        batch_size = min(self._auto_size_spin.value(), count)
        return [Path(self._thumb_grid.item(i).data(Qt.ItemDataRole.UserRole))
                for i in range(batch_size)]

    def _pick_next_auto_prompt(self) -> str:
        mode  = self._prompt_order_combo.currentData()
        texts = [e.text for e in self._prompts]
        n     = len(texts)

        if mode == "sequential":
            idx = self._auto_prompt_cursor % n
            self._auto_prompt_cursor += 1
            self._last_auto_prompt_idx = idx
            return texts[idx]

        if mode == "evens_odds":
            evens = texts[0::2]
            odds  = texts[1::2]
            seq   = evens + odds
            idx   = self._auto_prompt_cursor % len(seq)
            self._auto_prompt_cursor += 1
            self._last_auto_prompt_idx = idx
            return seq[idx]

        # weighted random — no consecutive repeat
        if n == 1:
            self._last_auto_prompt_idx = 0
        else:
            available = [i for i in range(n) if i != self._last_auto_prompt_idx]
            weights   = [self._prompts[i].weight for i in available]
            self._last_auto_prompt_idx = random.choices(available, weights=weights, k=1)[0]
        return texts[self._last_auto_prompt_idx]

    def _start_auto(self):
        batch = self._get_next_auto_batch()
        if not batch:
            QMessageBox.information(self, "Auto Run", "No images remaining in the grid.")
            return
        self._auto_mode = True
        self._auto_stop_requested = False
        self._auto_current_batch = batch
        self._update_auto_buttons()
        self._start(batch, clear_log=True, fixed_prompt=self._pick_next_auto_prompt())

    def _stop_auto_after_batch(self):
        self._auto_stop_requested = True
        self._stop_auto_btn.setEnabled(False)
        self._append_log("Stopping after current batch…")

    def _update_auto_buttons(self):
        show_all = self._show_all_chk.isChecked()
        self._auto_btn.setEnabled(not self._auto_mode and not show_all)
        self._auto_btn.setToolTip(
            "Disabled: uncheck 'Show all' before using Auto Run"
            if show_all else
            "Automatically process all images N at a time, no prompts between batches"
        )
        self._stop_auto_btn.setEnabled(self._auto_mode and not self._auto_stop_requested)

    # ------------------------------------------------------------------ #
    # Worker control
    # ------------------------------------------------------------------ #

    def _start(self, images: list[Path] | None = None, clear_log: bool = True,
               fixed_prompt: str | None = None):
        if clear_log:
            self._log_view.clear()
        if images is None:
            images = self._thumb_grid.all_paths()
        if not images:
            self._append_log("No images found. Select an input folder.")
            return
        if not self._prompts:
            self._append_log("No prompts loaded. Select a prompts file.")
            return
        if not Path(self._config.get("workflow_path", "")).is_file():
            self._append_log("No workflow JSON selected.")
            return
        if not self._config.get("output_dir", ""):
            self._append_log("No output folder selected.")
            return

        self._config.save()
        self._progress.setValue(0)
        self._progress.setMaximum(len(images))
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        pinned = {p.stem: text for p, text in
                  ((p, self._pinned.get(p.stem)) for p in images) if text}

        self._worker = BatchStyleWorker(
            config=self._config.get_all(),
            prompts=self._prompts,
            image_paths=images,
            fixed_prompt=fixed_prompt,
            prompt_mode=self._prompt_order_combo.currentData(),
            pinned=pinned,
            base_dir=self._base_dir,
        )
        self._worker.progress.connect(lambda cur, _: self._progress.setValue(cur))
        self._worker.log.connect(self._append_log)
        self._worker.all_done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel(self):
        if self._auto_mode:
            self._auto_mode = False
            self._auto_stop_requested = False
            self._auto_current_batch = []
            self._last_auto_prompt_idx = -1
            self._auto_prompt_cursor = 0
            self._update_auto_buttons()
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        # _on_done will fire from the worker after cancellation and refresh the grid

    def _on_done(self):
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._last_lib_dir = ""  # force library to reload next time it's opened

        if self._auto_mode:
            # Remove the batch we just finished from the grid
            processed_stems = {p.stem for p in self._auto_current_batch}
            if not self._show_all_chk.isChecked():
                self._thumb_grid.remove_items_by_stems(processed_stems)

            if not self._auto_stop_requested:
                next_batch = self._get_next_auto_batch()
                if next_batch:
                    self._auto_current_batch = next_batch
                    self._start(next_batch, clear_log=False,
                                fixed_prompt=self._pick_next_auto_prompt())
                    return
                # Grid exhausted
                self._append_log("Auto mode complete — no images remaining.")
            else:
                self._append_log("Auto mode stopped after batch.")

            self._auto_mode = False
            self._auto_stop_requested = False
            self._auto_current_batch = []
            self._last_auto_prompt_idx = -1
            self._auto_prompt_cursor = 0
            self._update_auto_buttons()
            self._reload_images()
            return

        self._reload_images()

    def _on_error(self, msg: str):
        self._append_log(f"ERROR: {msg}")
        self._auto_mode = False
        self._auto_stop_requested = False
        self._auto_current_batch = []
        self._last_auto_prompt_idx = -1
        self._update_auto_buttons()
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #

    def _append_log(self, msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        self._log_view.appendPlainText(f"[{now}] {msg}")

    def _update_mode_label(self):
        mode = self._config.get("mode", "local")
        if mode == "runpod":
            self._mode_lbl.setText("● RunPod")
            self._mode_lbl.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
        else:
            self._mode_lbl.setText("● Local")
            self._mode_lbl.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")

    def _update_status(self):
        mode = self._config.get("mode", "local")
        url  = (self._config.get("runpod_url", "")
                if mode == "runpod"
                else self._config.get("comfyui_url", "http://127.0.0.1:8000"))
        self._status.showMessage(f"ComfyUI:  {url}")

    def closeEvent(self, event):
        if self._loader:
            self._loader.cancel()
        if self._lib_loader and self._lib_loader.isRunning():
            self._lib_loader.cancel()
            self._lib_loader.wait(3000)
        if self._worker:
            self._worker.cancel()
        if self._reroll_worker:
            self._reroll_worker.cancel()
        self._config.save()
        super().closeEvent(event)
