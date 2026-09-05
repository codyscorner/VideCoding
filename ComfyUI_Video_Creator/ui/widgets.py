"""Thumbnail grid + background loaders + the folder browser panel used by
both tabs (images on tab 1, videos on tab 2).

Thumbnail caches use the same layout as the Chain Automator
(``<folder>/thumbnails/<stem>_<crc>.jpg`` for images, ``<stem>.jpg`` for
videos) so the two apps can share a cache when pointed at the same folder.
"""

from __future__ import annotations

import os
import zlib
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from media_tools import IMAGE_EXTS, VIDEO_EXTS, extract_last_frame, extract_thumbnail
from ui.styles import COLORS

THUMB_SIZE = 200

SORT_OPTIONS = ["Name A→Z", "Name Z→A", "Newest First", "Oldest First"]


def sort_params(option: str):
    if option == "Name Z→A":
        return (lambda p: p.name.lower()), True
    if option == "Newest First":
        return (lambda p: p.stat().st_mtime), True
    if option == "Oldest First":
        return (lambda p: p.stat().st_mtime), False
    return (lambda p: p.name.lower()), False


# --------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------- #

class ElidedLabel(QLabel):
    """Single-line label that elides its text to the available width and
    shows the full text as a tooltip."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = ""
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFullText(text)

    def setFullText(self, text: str):
        self._full = text or ""
        self.setToolTip(self._full)
        self._refresh()

    def fullText(self) -> str:
        return self._full

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        width = max(self.width() - 4, 40)
        super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width))


# --------------------------------------------------------------------- #
# Grid
# --------------------------------------------------------------------- #

class ThumbnailGrid(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 14, THUMB_SIZE + 30))
        self.setSpacing(4)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px;"
            f" font-family: 'Segoe UI'; font-size: 8.5pt; padding-right: 12px; }}"
            f"QListWidget::item {{ border: 2px solid transparent; border-radius: 4px; color: {COLORS['fg_secondary']}; }}"
            f"QListWidget::item:selected {{ background-color: {COLORS['accent_dark']};"
            f" border: 2px solid {COLORS['accent_hover']}; border-radius: 4px; color: white; }}"
            f"QListWidget::item:hover:!selected {{ border: 2px solid {COLORS['border']}; }}"
        )

    def add_item(self, img: QImage, key: str, label: str):
        pix = QPixmap.fromImage(img)
        canvas = QPixmap(THUMB_SIZE, THUMB_SIZE)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        painter.drawPixmap((THUMB_SIZE - pix.width()) // 2, (THUMB_SIZE - pix.height()) // 2, pix)
        painter.end()
        item = QListWidgetItem(QIcon(canvas), label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setToolTip(key)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.addItem(item)

    def selected_key(self) -> str | None:
        items = self.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def select_key(self, key: str) -> bool:
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self.setCurrentItem(item)
                self.scrollToItem(item)
                return True
        return False


# --------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------- #

class ImageLoaderThread(QThread):
    item_ready = pyqtSignal(QImage, str, str)   # image, absolute path, label
    progress = pyqtSignal(int, int)
    finished_loading = pyqtSignal(int)

    def __init__(self, folder: Path, sort_option: str):
        super().__init__()
        self._folder = folder
        self._sort_key, self._reverse = sort_params(sort_option)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _thumb_name(self, img_path: Path) -> str:
        rel = str(img_path.relative_to(self._folder))
        return f"{img_path.stem}_{zlib.crc32(rel.lower().encode()):08x}.jpg"

    def run(self):
        thumb_dir = self._folder / "thumbnails"
        try:
            thumb_dir.mkdir(exist_ok=True)
        except OSError:
            thumb_dir = None

        try:
            images = sorted(
                (p for p in self._folder.rglob("*")
                 if p.suffix.lower() in IMAGE_EXTS
                 and (thumb_dir is None or thumb_dir not in p.parents)),
                key=self._sort_key, reverse=self._reverse,
            )
        except OSError:
            images = []

        total = len(images)
        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            img = QImage()
            thumb_path = thumb_dir / self._thumb_name(img_path) if thumb_dir else None
            try:
                if (thumb_path and thumb_path.exists()
                        and thumb_path.stat().st_mtime >= img_path.stat().st_mtime):
                    img = QImage(str(thumb_path))
            except OSError:
                pass
            if img.isNull():
                try:
                    pil_img = Image.open(img_path)
                    pil_img = ImageOps.exif_transpose(pil_img)
                    pil_img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
                    pil_img = pil_img.convert("RGB")
                    if thumb_path:
                        try:
                            pil_img.save(thumb_path, "JPEG", quality=88)
                        except OSError:
                            pass
                    data = pil_img.convert("RGBA").tobytes("raw", "RGBA")
                    img = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888).copy()
                except Exception:
                    img = QImage(str(img_path))
                    if not img.isNull():
                        img = img.scaled(THUMB_SIZE, THUMB_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            if img.isNull():
                continue
            rel = img_path.relative_to(self._folder)
            label = str(rel) if rel.parent != Path(".") else img_path.name
            self.item_ready.emit(img, str(img_path), label)
            loaded += 1
            self.progress.emit(loaded, total)
        self.finished_loading.emit(loaded)


class VideoLoaderThread(QThread):
    item_ready = pyqtSignal(QImage, str, str)
    progress = pyqtSignal(int, int)
    finished_loading = pyqtSignal(int)

    def __init__(self, folder: Path, ffmpeg: str, sort_option: str, last_frame: bool = True):
        super().__init__()
        self._folder = folder
        self._ffmpeg = ffmpeg
        self._sort_key, self._reverse = sort_params(sort_option)
        self._last_frame = last_frame
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        thumb_dir = self._folder / "thumbnails"
        try:
            thumb_dir.mkdir(exist_ok=True)
        except OSError:
            pass
        try:
            videos = sorted(
                (p for p in self._folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS),
                key=self._sort_key, reverse=self._reverse,
            )
        except OSError:
            videos = []

        total = len(videos)
        loaded = 0
        for vid in videos:
            if self._cancelled:
                return
            # The Extend tab shows each video's LAST frame — that's the
            # starting point of the extension. Cached under its own name so
            # it never collides with the Chain Automator's first-frame cache.
            thumb = thumb_dir / (vid.stem + ("_last.jpg" if self._last_frame else ".jpg"))
            try:
                stale = thumb.exists() and thumb.stat().st_mtime < vid.stat().st_mtime
            except OSError:
                stale = False
            if not thumb.exists() or stale:
                if self._last_frame:
                    try:
                        extract_last_frame(self._ffmpeg, vid, thumb)
                    except Exception:
                        extract_thumbnail(self._ffmpeg, vid, thumb)
                else:
                    extract_thumbnail(self._ffmpeg, vid, thumb)
            img = QImage(str(thumb)) if thumb.exists() else QImage()
            if img.isNull():
                img = QImage(THUMB_SIZE, THUMB_SIZE, QImage.Format.Format_RGB32)
                img.fill(QColor(COLORS['bg_light']))
            else:
                img = img.scaled(THUMB_SIZE, THUMB_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            self.item_ready.emit(img, str(vid), vid.name)
            loaded += 1
            self.progress.emit(loaded, total)
        self.finished_loading.emit(loaded)


# --------------------------------------------------------------------- #
# Browser panel
# --------------------------------------------------------------------- #

class MediaBrowser(QWidget):
    """Folder row + sort + thumbnail grid for one media kind."""
    selection_changed = pyqtSignal(object)   # Path | None
    activated = pyqtSignal(object)           # Path (double-click)
    folder_changed = pyqtSignal(str)
    sort_changed = pyqtSignal(str)

    def __init__(self, kind: str, folder: str, sort_option: str, ffmpeg_getter, parent=None,
                 multi: bool = False, last_frame: bool = True, title: str | None = None, hint: str = ""):
        super().__init__(parent)
        self.kind = kind                      # "image" | "video"
        self._folder = folder
        self._ffmpeg_getter = ffmpeg_getter
        self._last_frame = last_frame
        self._loader: QThread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)
        noun = "Image" if kind == "image" else "Video"
        lbl = QLabel(f"{title or noun} Folder:")
        lbl.setStyleSheet(f"color: {COLORS['accent_hover']}; font-weight: bold;")
        row.addWidget(lbl)
        self._path_edit = QLineEdit(folder)
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText(f"Pick the folder that holds your {noun.lower()}s…")
        row.addWidget(self._path_edit, stretch=1)
        browse = QPushButton("…")
        browse.setObjectName("small_btn")
        browse.setFixedWidth(36)
        browse.setToolTip("Choose folder")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        refresh = QPushButton("↻")
        refresh.setObjectName("small_btn")
        refresh.setFixedWidth(36)
        refresh.setToolTip("Rescan folder")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        open_btn = QPushButton("📂")
        open_btn.setObjectName("small_btn")
        open_btn.setFixedWidth(40)
        open_btn.setToolTip("Open folder in Explorer")
        open_btn.clicked.connect(self._open_folder)
        row.addWidget(open_btn)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(SORT_OPTIONS)
        if sort_option in SORT_OPTIONS:
            self._sort_combo.setCurrentText(sort_option)
        self._sort_combo.currentTextChanged.connect(self._on_sort)
        row2.addWidget(self._sort_combo)
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("status_dim")
            row2.addSpacing(12)
            row2.addWidget(hint_lbl)
        row2.addStretch()
        self._status = QLabel("")
        self._status.setObjectName("status_dim")
        row2.addWidget(self._status)
        layout.addLayout(row2)

        self.grid = ThumbnailGrid()
        if multi:
            self.grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.grid.itemSelectionChanged.connect(self._on_selection)
        self.grid.itemDoubleClicked.connect(lambda it: self.activated.emit(Path(it.data(Qt.ItemDataRole.UserRole))))
        layout.addWidget(self.grid, stretch=1)

    # ------------------------------------------------------------------ #

    @property
    def folder(self) -> str:
        return self._folder

    def set_folder(self, folder: str):
        self._folder = folder or ""
        self._path_edit.setText(self._folder)
        self.refresh()

    def selected_path(self) -> Path | None:
        key = self.grid.selected_key()
        return Path(key) if key else None

    def selected_paths(self) -> list[Path]:
        return [Path(it.data(Qt.ItemDataRole.UserRole)) for it in self.grid.selectedItems()]

    def _browse(self):
        start = self._folder if self._folder and Path(self._folder).is_dir() else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, f"Select {self.kind} folder", start)
        if not folder:
            return
        if Path(folder).name.lower() == "thumbnails":
            folder = str(Path(folder).parent)
        self._folder = folder
        self._path_edit.setText(folder)
        self.folder_changed.emit(folder)
        self.refresh()

    def _open_folder(self):
        if self._folder and Path(self._folder).is_dir():
            os.startfile(self._folder)

    def _on_sort(self, text: str):
        self.sort_changed.emit(text)
        self.refresh()

    def _on_selection(self):
        self.selection_changed.emit(self.selected_path())

    def refresh(self):
        previous = self.grid.selected_key()
        if self._loader is not None and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait(3000)
        self.grid.clear()
        self.selection_changed.emit(None)
        folder = Path(self._folder) if self._folder else None
        if not folder or not folder.is_dir():
            self._status.setText("No folder selected" if not self._folder else "Folder not found")
            return
        self._status.setText("Loading…")
        sort_option = self._sort_combo.currentText()
        if self.kind == "image":
            self._loader = ImageLoaderThread(folder, sort_option)
        else:
            self._loader = VideoLoaderThread(folder, self._ffmpeg_getter(), sort_option, last_frame=self._last_frame)
        self._loader.item_ready.connect(self.grid.add_item)
        self._loader.progress.connect(lambda c, t: self._status.setText(f"Loading {c}/{t}…"))
        self._loader.finished_loading.connect(lambda n: self._on_loaded(n, previous))
        self._loader.start()

    def _on_loaded(self, n: int, previous: str | None):
        noun = "image" if self.kind == "image" else "video"
        self._status.setText(f"{n} {noun}{'s' if n != 1 else ''}")
        if previous:
            self.grid.select_key(previous)

    def shutdown(self):
        if self._loader is not None and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait(3000)
