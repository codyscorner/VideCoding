import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QSplitter, QHBoxLayout, QVBoxLayout, QFileDialog,
    QMessageBox, QDoubleSpinBox, QStatusBar, QCheckBox, QComboBox,
    QApplication, QMenu, QProgressDialog,
)
from PyQt6.QtCore import Qt, QRect, QTimer, QPoint, QUrl, QMimeData, pyqtSlot
from PyQt6.QtGui import QKeyEvent, QPixmap

from config import ConfigManager
from app.ratings import RatingsStore
from app.edit_ops import apply_edits
from app.ui.styles import STYLESHEET, COLORS
from app.ui.filmstrip import FilmStrip
from app.ui.image_viewer import ImageViewer
from app.ui.image_info_bar import ImageInfoBar
from app.ui.slideshow import SlideshowWindow
from app.ui.compare_dialog import CompareDialog
from app.ui.similarity_dialog import SimilarityDialog
from app.workers.thumbnail_worker import (
    ThumbnailWorker, SUPPORTED_EXTENSIONS, THUMB_SOURCE_SIZE,
    is_video, load_video_frame,
)
from app.workers.similarity_worker import SimilarityIndexWorker
from app.workers.similarity_search_worker import SimilaritySearchWorker
from app.similarity_cache import SimilarityCache
from app.similarity import compute_fingerprint

FILTER_OPTIONS = [
    ("All", None),
    ("Flagged ⚑", "flagged"),
    ("★ 1+", 1),
    ("★★ 2+", 2),
    ("★★★ 3+", 3),
    ("★★★★ 4+", 4),
    ("★★★★★ 5", 5),
]


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version
        self.ratings = RatingsStore(
            self.config.config_file.parent / "photo_gallery_ratings.json"
        )

        self._all_paths: List[str] = []      # every file found in the folder
        self._image_paths: List[str] = []    # after rating/flag filter
        self._current_index: int = -1
        self._thumbnail_worker: Optional[ThumbnailWorker] = None
        self._slideshow_window: Optional[SlideshowWindow] = None
        self._pending_crop: Optional[QRect] = None
        self._compare_armed: bool = False
        self._search_text: str = ""
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(250)
        self._search_debounce.timeout.connect(self._apply_filter)

        self._similarity_cache = SimilarityCache(
            self.config.config_file.parent / "photo_gallery_similarity_cache.sqlite3"
        )
        self._similarity_index_worker: Optional[SimilarityIndexWorker] = None
        self._similarity_search_worker: Optional[SimilaritySearchWorker] = None
        self._similarity_order: Optional[List[str]] = None   # ranked paths, best match first
        self._similarity_scores: dict = {}                   # path -> 0..1 score for display
        self._similarity_faces_only: bool = False
        self._face_tolerance: float = self.config.get("similarity_face_tolerance", 0.6)

        self.setWindowTitle(f"Photo Gallery v{self.version}")
        self.setMinimumSize(900, 600)
        self.resize(
            self.config.get("window_width", 1200),
            self.config.get("window_height", 750),
        )
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_signals()
        self._load_initial_state()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_actions_bar())

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._filmstrip = FilmStrip(self.config.get("thumbnail_size", 120))
        self._viewer = ImageViewer()
        self._splitter.addWidget(self._filmstrip)
        self._splitter.addWidget(self._viewer)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setCollapsible(0, False)
        strip_width = self.config.get(
            "filmstrip_width", self.config.get("thumbnail_size", 120) + 14
        )
        window_width = self.config.get("window_width", 1200)
        self._splitter.setSizes([strip_width, max(300, window_width - strip_width)])
        root.addWidget(self._splitter, stretch=1)

        root.addWidget(self._build_bottom_bar())

        self._info_bar = ImageInfoBar()
        root.addWidget(self._info_bar)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("Select a folder containing images...")
        layout.addWidget(self._folder_edit, stretch=1)

        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(100)
        self._browse_btn.clicked.connect(self._browse_folder)
        layout.addWidget(self._browse_btn)

        self._subfolders_check = QCheckBox("Include subfolders")
        self._subfolders_check.setStyleSheet(f"color: {COLORS['fg_secondary']}; spacing: 6px;")
        self._subfolders_check.setToolTip("Scan images in all subfolders (useful for photo albums)")
        self._subfolders_check.stateChanged.connect(self._on_subfolder_toggle)
        layout.addWidget(self._subfolders_check)

        layout.addSpacing(16)

        delay_label = QLabel("Delay (s):")
        delay_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(delay_label)

        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.5, 60.0)
        self._delay_spin.setSingleStep(0.5)
        self._delay_spin.setDecimals(1)
        self._delay_spin.setFixedWidth(72)
        self._delay_spin.setToolTip("Time between images in slideshow mode")
        layout.addWidget(self._delay_spin)

        fade_label = QLabel("Fade (s):")
        fade_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(fade_label)

        self._fade_spin = QDoubleSpinBox()
        self._fade_spin.setRange(0.0, 3.0)
        self._fade_spin.setSingleStep(0.5)
        self._fade_spin.setDecimals(1)
        self._fade_spin.setFixedWidth(64)
        self._fade_spin.setToolTip("Fade transition duration between images (0 = instant)")
        layout.addWidget(self._fade_spin)

        self._slideshow_btn = QPushButton("Start Slideshow")
        self._slideshow_btn.setObjectName("slideshow_btn")
        self._slideshow_btn.setEnabled(False)
        self._slideshow_btn.clicked.connect(self._start_slideshow)
        layout.addWidget(self._slideshow_btn)

        return bar

    def _build_actions_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        filter_label = QLabel("Show:")
        filter_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        layout.addWidget(filter_label)

        self._filter_combo = QComboBox()
        for label, _ in FILTER_OPTIONS:
            self._filter_combo.addItem(label)
        self._filter_combo.setFixedWidth(130)
        self._filter_combo.setToolTip("Filter images by rating or flag (keys 1-5 rate, 0 clears, F flags)")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_combo)

        layout.addSpacing(8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search filename...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setFixedWidth(220)
        self._search_edit.setToolTip("Filter thumbnails by filename (case-insensitive substring)")
        self._search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_edit)

        self._find_similar_btn = QPushButton("Find Similar...")
        self._find_similar_btn.setEnabled(False)
        self._find_similar_btn.setToolTip(
            "Pick or paste a reference image to find similar/matching-face photos in this folder"
        )
        self._find_similar_btn.clicked.connect(self._open_similarity_dialog)
        layout.addWidget(self._find_similar_btn)

        self._clear_similarity_btn = QPushButton("✕ Clear Similarity")
        self._clear_similarity_btn.setVisible(False)
        self._clear_similarity_btn.clicked.connect(self._clear_similarity)
        layout.addWidget(self._clear_similarity_btn)

        self._rating_label = QLabel("")
        self._rating_label.setStyleSheet(f"color: #facc15; font-size: 11pt;")
        self._rating_label.setFixedWidth(120)
        self._rating_label.setToolTip("Current image rating/flag — press 1-5 to rate, 0 to clear, F to flag")
        layout.addWidget(self._rating_label)

        layout.addStretch(1)

        self._compare_btn = QPushButton("Compare...")
        self._compare_btn.setEnabled(False)
        self._compare_btn.setToolTip("Click, then click another thumbnail to compare it with the current image")
        self._compare_btn.clicked.connect(self._arm_compare)
        layout.addWidget(self._compare_btn)

        self._crop_btn = QPushButton("Select Area")
        self._crop_btn.setCheckable(True)
        self._crop_btn.setEnabled(False)
        self._crop_btn.setToolTip(
            "Drag a rectangle on the image (Esc cancels) — use it to copy that "
            "area, search for similar images, or crop-and-save a copy"
        )
        self._crop_btn.toggled.connect(self._on_crop_toggled)
        layout.addWidget(self._crop_btn)

        self._copy_selection_btn = QPushButton("Copy Selection")
        self._copy_selection_btn.setEnabled(False)
        self._copy_selection_btn.setToolTip(
            "Copy the selected area to the clipboard as an image (Ctrl+V to paste elsewhere)"
        )
        self._copy_selection_btn.clicked.connect(self._copy_selection_to_clipboard)
        layout.addWidget(self._copy_selection_btn)

        self._find_similar_selection_btn = QPushButton("Find Similar (Selection)")
        self._find_similar_selection_btn.setEnabled(False)
        self._find_similar_selection_btn.setToolTip(
            "Search this folder for images similar to the selected area"
        )
        self._find_similar_selection_btn.clicked.connect(self._find_similar_from_selection)
        layout.addWidget(self._find_similar_selection_btn)

        self._save_as_btn = QPushButton("Save As...")
        self._save_as_btn.setEnabled(False)
        self._save_as_btn.setToolTip(
            "Save the rotated/cropped result to a NEW file — the original is never modified"
        )
        self._save_as_btn.clicked.connect(self._save_edits)
        layout.addWidget(self._save_as_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.setStyleSheet("background-color: #b91c1c;")
        self._delete_btn.setToolTip("Send the current file to the Recycle Bin (Del)")
        self._delete_btn.clicked.connect(self._delete_current)
        layout.addWidget(self._delete_btn)

        return bar

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_medium']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setFixedWidth(90)
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(lambda: self._navigate(-1))
        layout.addWidget(self._prev_btn)

        self._counter_label = QLabel("No images")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter_label.setObjectName("subtitle")
        layout.addWidget(self._counter_label, stretch=1)

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setFixedWidth(90)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(lambda: self._navigate(1))
        layout.addWidget(self._next_btn)

        return bar

    # ── Signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._filmstrip.image_selected.connect(self._on_image_selected)
        self._viewer.crop_selected.connect(self._on_crop_selected)
        self._viewer.activated.connect(self._open_current_video)
        self._viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._viewer.customContextMenuRequested.connect(self._show_viewer_context_menu)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_initial_state(self) -> None:
        self._delay_spin.setValue(self.config.get("slideshow_delay", 3.0))
        self._fade_spin.setValue(self.config.get("fade_duration", 0.5))
        self._subfolders_check.setChecked(self.config.get("include_subfolders", False))
        last_folder = self.config.get("last_folder", "")
        if last_folder:
            self._folder_edit.setText(last_folder)
            if os.path.isdir(last_folder):
                self._scan_folder(last_folder)

    def _save_config(self) -> None:
        self.config.set("last_folder", self._folder_edit.text())
        self.config.set("slideshow_delay", self._delay_spin.value())
        self.config.set("fade_duration", self._fade_spin.value())
        self.config.set("include_subfolders", self._subfolders_check.isChecked())
        self.config.set("similarity_face_tolerance", self._face_tolerance)
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())
        self.config.set("filmstrip_width", self._filmstrip.width())
        self.config.save()

    # ── Folder Scanning ───────────────────────────────────────────────────────

    @pyqtSlot()
    def _browse_folder(self) -> None:
        existing = self._folder_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", start)
        if folder:
            self._folder_edit.setText(folder)
            self._scan_folder(folder)

    @pyqtSlot()
    def _on_subfolder_toggle(self) -> None:
        folder = self._folder_edit.text().strip()
        if folder and os.path.isdir(folder):
            self._scan_folder(folder)

    def _scan_folder(self, folder: str) -> None:
        root = Path(folder)
        recursive = self._subfolders_check.isChecked()
        try:
            if recursive:
                entries = sorted(
                    p for ext in SUPPORTED_EXTENSIONS
                    for p in root.rglob(f"*{ext}")
                    if p.is_file()
                )
            else:
                entries = sorted(p for p in root.iterdir() if p.is_file())
        except PermissionError:
            QMessageBox.critical(self, "Error", f"Cannot read folder:\n{folder}")
            return

        self._all_paths = [
            str(p) for p in entries
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        self._clear_similarity(rerun_filter=False)
        self._apply_filter()
        stills = [p for p in self._all_paths if not is_video(p)]
        if stills:
            self._restart_similarity_indexing(stills)

    def _restart_similarity_indexing(self, paths: List[str]) -> None:
        if self._similarity_index_worker and self._similarity_index_worker.isRunning():
            self._similarity_index_worker.cancel()
            self._similarity_index_worker.wait()
        worker = SimilarityIndexWorker(paths, self._similarity_cache)
        worker.progress.connect(self._on_similarity_index_progress)
        worker.finished_ok.connect(self._on_similarity_index_done)
        worker.error.connect(lambda msg: None)
        self._similarity_index_worker = worker
        worker.start()

    @pyqtSlot(int, int)
    def _on_similarity_index_progress(self, done: int, total: int) -> None:
        if done == 0 or done == total or done % 200 == 0:
            self.statusBar().showMessage(
                f"Indexing for similarity search: {done} / {total}...", 0
            )

    @pyqtSlot()
    def _on_similarity_index_done(self) -> None:
        self._similarity_index_worker = None
        self.statusBar().showMessage("Similarity index up to date.", 4000)

    def _current_filter(self):
        return FILTER_OPTIONS[self._filter_combo.currentIndex()][1]

    def _passes_filter(self, path: str) -> bool:
        if self._search_text and self._search_text not in Path(path).name.lower():
            return False
        rule = self._current_filter()
        if rule is None:
            return True
        if rule == "flagged":
            return self.ratings.is_flagged(path)
        return self.ratings.get_rating(path) >= rule

    def _apply_filter(self) -> None:
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            self._thumbnail_worker.cancel()
            self._thumbnail_worker.wait()

        current_path = (
            self._image_paths[self._current_index]
            if 0 <= self._current_index < len(self._image_paths) else None
        )
        if self._similarity_order:
            all_set = set(self._all_paths)
            ordered = [p for p in self._similarity_order if p in all_set]
            self._image_paths = [p for p in ordered if self._passes_filter(p)]
        else:
            self._image_paths = [p for p in self._all_paths if self._passes_filter(p)]
        self._cancel_edit_state()
        self._compare_armed = False

        if not self._image_paths:
            self._viewer.clear_image()
            self._filmstrip.populate([])
            self._info_bar.clear()
            self._current_index = -1
            self._update_nav_controls()
            msg = ("No supported images in this folder."
                   if not self._all_paths else "No images match the current filter.")
            self._counter_label.setText("No images")
            self.statusBar().showMessage(msg)
            return

        self._filmstrip.populate(self._image_paths)
        start = 0
        if current_path and current_path in self._image_paths:
            start = self._image_paths.index(current_path)
        self._show_image(start)

        self._thumbnail_worker = ThumbnailWorker(
            self._image_paths,
            thumbnail_size=THUMB_SOURCE_SIZE,
        )
        self._thumbnail_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumbnail_worker.finished.connect(self._on_thumbnails_done)
        self._thumbnail_worker.error.connect(self._on_worker_error)
        self._thumbnail_worker.start()

        self.statusBar().showMessage(
            f"Loading thumbnails for {len(self._image_paths)} files..."
        )

    @pyqtSlot(int, QPixmap)
    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap) -> None:
        self._filmstrip.set_thumbnail(index, pixmap)
        self._refresh_badges(index)

    def _refresh_badges(self, index: int) -> None:
        if 0 <= index < len(self._image_paths):
            path = self._image_paths[index]
            self._filmstrip.set_badges(
                index,
                rating=self.ratings.get_rating(path),
                flagged=self.ratings.is_flagged(path),
                is_video=is_video(path),
            )

    @pyqtSlot()
    def _on_filter_changed(self) -> None:
        if self._all_paths:
            self._apply_filter()

    @pyqtSlot(str)
    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip().lower()
        if self._all_paths:
            self._search_debounce.start()

    # ── Image Display ─────────────────────────────────────────────────────────

    def _show_image(self, index: int) -> None:
        if not (0 <= index < len(self._image_paths)):
            return
        self._cancel_edit_state()
        self._current_index = index
        path = self._image_paths[index]
        if is_video(path):
            qimage = load_video_frame(path)
            if qimage is not None:
                self._viewer.show_pixmap(QPixmap.fromImage(qimage))
                self.statusBar().showMessage(
                    "Video — press Enter or double-click to play in your default player."
                )
            else:
                self._viewer.clear_image()
                self._viewer.setText("Video (no preview) — press Enter to play")
        else:
            self._viewer.show_image(path)
        self._filmstrip.select_index(index)
        self._info_bar.update_image(path)
        self._update_nav_controls()
        self._update_rating_label()
        self._update_edit_controls()

    def _update_nav_controls(self) -> None:
        total = len(self._image_paths)
        has_images = total > 0
        idx = self._current_index
        self._prev_btn.setEnabled(has_images and idx > 0)
        self._next_btn.setEnabled(has_images and idx < total - 1)
        self._slideshow_btn.setEnabled(has_images)
        self._compare_btn.setEnabled(total > 1)
        self._delete_btn.setEnabled(has_images and 0 <= idx < total)
        self._find_similar_btn.setEnabled(bool(self._all_paths))
        if has_images and 0 <= idx < total:
            path = self._image_paths[idx]
            name = Path(path).name
            text = f"{idx + 1} of {total}  —  {name}"
            score = self._similarity_scores.get(path)
            if score is not None:
                text += f"  —  {score * 100:.0f}% match"
            self._counter_label.setText(text)
        else:
            self._counter_label.setText("No images")

    def _update_rating_label(self) -> None:
        path = self._current_path()
        if not path:
            self._rating_label.setText("")
            return
        rating = self.ratings.get_rating(path)
        flagged = self.ratings.is_flagged(path)
        text = ("⚑ " if flagged else "") + ("★" * rating if rating else "")
        self._rating_label.setText(text or "—")

    def _update_edit_controls(self) -> None:
        path = self._current_path()
        editable = bool(path) and not is_video(path or "")
        self._crop_btn.setEnabled(editable)
        has_selection = editable and self._pending_crop is not None
        has_edits = editable and (self._viewer.rotation != 0 or self._pending_crop is not None)
        self._save_as_btn.setEnabled(has_edits)
        self._copy_selection_btn.setEnabled(has_selection)
        self._find_similar_selection_btn.setEnabled(has_selection and bool(self._all_paths))

    def _current_path(self) -> Optional[str]:
        if 0 <= self._current_index < len(self._image_paths):
            return self._image_paths[self._current_index]
        return None

    # ── Ratings / Flags ───────────────────────────────────────────────────────

    def _set_rating(self, rating: int) -> None:
        path = self._current_path()
        if not path:
            return
        self.ratings.set_rating(path, rating)
        self._update_rating_label()
        self._refresh_badges(self._current_index)
        self.statusBar().showMessage(
            f"Rating: {'★' * rating if rating else 'cleared'}", 3000
        )

    def _toggle_flag(self) -> None:
        path = self._current_path()
        if not path:
            return
        state = self.ratings.toggle_flag(path)
        self._update_rating_label()
        self._refresh_badges(self._current_index)
        self.statusBar().showMessage("Flagged ⚑" if state else "Flag removed", 3000)

    # ── Find Similar ──────────────────────────────────────────────────────────

    @pyqtSlot()
    def _open_similarity_dialog(self) -> None:
        dialog = SimilarityDialog(self, face_tolerance=self._face_tolerance)
        if dialog.exec() != SimilarityDialog.DialogCode.Accepted or not dialog.reference_path:
            return
        self._face_tolerance = dialog.face_tolerance
        self._run_similarity_search(dialog.reference_path, dialog.face_tolerance)

    def _run_similarity_search(self, reference_path: str, face_tolerance: float) -> None:
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            ref_fingerprint = compute_fingerprint(reference_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read that image:\n{e}")
            return
        finally:
            self.unsetCursor()

        if self._similarity_search_worker and self._similarity_search_worker.isRunning():
            self._similarity_search_worker.cancel()
            self._similarity_search_worker.wait()

        progress = QProgressDialog("Searching for matches...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Find Similar")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        worker = SimilaritySearchWorker(
            self._all_paths, self._similarity_cache, ref_fingerprint, face_tolerance
        )
        worker.finished_ok.connect(
            lambda order, scores, used_faces, indexed, total_all: self._on_similarity_search_done(
                progress, order, scores, used_faces, indexed, total_all
            )
        )
        worker.error.connect(lambda msg: self._on_similarity_search_error(progress, msg))
        progress.canceled.connect(worker.cancel)
        self._similarity_search_worker = worker
        worker.start()
        progress.exec()

    def _on_similarity_search_done(
        self, progress: "QProgressDialog", order: List[str], scores: dict,
        used_faces: bool, indexed: int, total_all: int,
    ) -> None:
        progress.close()
        self._similarity_search_worker = None

        if not order and indexed == 0:
            QMessageBox.information(
                self, "Not Indexed Yet",
                "Similarity indexing hasn't finished for this folder yet.\n"
                "Wait a bit and try again — indexing runs in the background."
            )
            return

        self._similarity_order = order
        self._similarity_scores = scores
        self._similarity_faces_only = used_faces
        self._clear_similarity_btn.setVisible(True)
        self._apply_filter()

        mode = "face match" if used_faces else "visual similarity"
        msg = f"Find Similar ({mode}): {len(order)} result(s) from {indexed} of {total_all} indexed images."
        if indexed < total_all:
            msg += " Indexing is still running — results will improve."
        self.statusBar().showMessage(msg, 8000)

    def _on_similarity_search_error(self, progress: "QProgressDialog", message: str) -> None:
        progress.close()
        self._similarity_search_worker = None
        QMessageBox.critical(self, "Search Failed", message)

    def _clear_similarity(self, rerun_filter: bool = True) -> None:
        self._similarity_order = None
        self._similarity_scores = {}
        self._similarity_faces_only = False
        self._clear_similarity_btn.setVisible(False)
        if rerun_filter and self._all_paths:
            self._apply_filter()

    # ── Compare ───────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _arm_compare(self) -> None:
        if len(self._image_paths) < 2 or self._current_index < 0:
            return
        self._compare_armed = True
        self.statusBar().showMessage(
            "Compare: click another thumbnail to compare with the current image (Esc cancels)."
        )

    # ── Edit ops ──────────────────────────────────────────────────────────────

    @pyqtSlot(bool)
    def _on_crop_toggled(self, checked: bool) -> None:
        self._viewer.set_crop_mode(checked)
        if checked:
            self.statusBar().showMessage(
                "Selection: drag a rectangle, then Copy Selection / Find Similar (Selection) / Save As (Esc cancels)."
            )
        else:
            self._pending_crop = None
            self._update_edit_controls()

    @pyqtSlot(QRect)
    def _on_crop_selected(self, rect: QRect) -> None:
        self._pending_crop = rect
        self._update_edit_controls()
        self.statusBar().showMessage(
            f"Selected: {rect.width()} × {rect.height()} px — "
            "Copy Selection, Find Similar (Selection), or Save As.", 0
        )

    def _cancel_edit_state(self) -> None:
        self._pending_crop = None
        if self._crop_btn.isChecked():
            self._crop_btn.setChecked(False)
        self._viewer.set_crop_mode(False)

    def _copy_selection_to_clipboard(self) -> None:
        if self._pending_crop is None:
            return
        pixmap = self._viewer.cropped_pixmap(self._pending_crop)
        if pixmap is None or pixmap.isNull():
            return
        QApplication.clipboard().setPixmap(pixmap)
        self.statusBar().showMessage("Selection copied to clipboard as an image.", 4000)

    def _find_similar_from_selection(self) -> None:
        if self._pending_crop is None:
            return
        pixmap = self._viewer.cropped_pixmap(self._pending_crop)
        if pixmap is None or pixmap.isNull():
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_path = os.path.join(tempfile.gettempdir(), f"photogallery_selection_{stamp}.png")
        pixmap.save(temp_path, "PNG")
        dialog = SimilarityDialog(
            self, face_tolerance=self._face_tolerance, initial_reference_path=temp_path
        )
        if dialog.exec() != SimilarityDialog.DialogCode.Accepted or not dialog.reference_path:
            return
        self._face_tolerance = dialog.face_tolerance
        self._run_similarity_search(dialog.reference_path, dialog.face_tolerance)

    def _save_edits(self) -> None:
        # The original file is never modified — this always writes a new file.
        path = self._current_path()
        if not path or is_video(path):
            return
        rotation = self._viewer.rotation
        crop = self._pending_crop
        if rotation == 0 and crop is None:
            return

        suffix = Path(path).suffix
        suggested = str(Path(path).with_name(Path(path).stem + "_edited" + suffix))
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Image As", suggested,
            f"Image (*{suffix})",
        )
        if not dest:
            return
        if os.path.normpath(dest) == os.path.normpath(path):
            QMessageBox.warning(
                self, "Cannot Overwrite Original",
                "This app never modifies the original file — please choose a different filename."
            )
            return

        crop_box = None
        if crop is not None:
            crop_box = (crop.left(), crop.top(), crop.right() + 1, crop.bottom() + 1)

        try:
            written = apply_edits(path, rotation=rotation, crop_box=crop_box, dest_path=dest)
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save image:\n{e}")
            return

        self._cancel_edit_state()
        self._update_edit_controls()
        self.statusBar().showMessage(f"Saved copy: {written}", 5000)

    # ── Delete ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _delete_current(self) -> None:
        path = self._current_path()
        if not path:
            return
        reply = QMessageBox.question(
            self, "Delete File",
            f"Send this file to the Recycle Bin?\n\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from send2trash import send2trash
            send2trash(os.path.normpath(path))
        except Exception as e:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete file:\n{e}")
            return

        self.ratings.remove(path)
        idx = self._current_index
        self._all_paths.remove(path)
        self._image_paths.pop(idx)
        self._filmstrip.remove_index(idx)

        if not self._image_paths:
            self._viewer.clear_image()
            self._info_bar.clear()
            self._current_index = -1
            self._update_nav_controls()
            self._update_rating_label()
            self._update_edit_controls()
        else:
            self._show_image(min(idx, len(self._image_paths) - 1))
        self.statusBar().showMessage("Sent to Recycle Bin.", 5000)

    # ── File context menu ────────────────────────────────────────────────────

    @pyqtSlot(QPoint)
    def _show_viewer_context_menu(self, pos: QPoint) -> None:
        path = self._current_path()
        if not path:
            return
        menu = QMenu(self)
        menu.addAction("Copy File Path", lambda: self._copy_text_to_clipboard(path))
        menu.addAction("Copy File Name", lambda: self._copy_text_to_clipboard(Path(path).name))
        menu.addAction("Copy Folder Path", lambda: self._copy_text_to_clipboard(str(Path(path).parent)))
        menu.addSeparator()
        menu.addAction("Copy File", lambda: self._copy_file_to_clipboard(path))
        menu.addSeparator()
        menu.addAction("Reveal in Explorer", lambda: self._reveal_in_explorer(path))
        menu.exec(self._viewer.mapToGlobal(pos))

    def _copy_text_to_clipboard(self, text: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(f"Copied to clipboard: {text}", 4000)

    def _copy_file_to_clipboard(self, path: str) -> None:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        QApplication.clipboard().setMimeData(mime)
        self.statusBar().showMessage(
            "File copied — press Ctrl+V in Explorer to paste a copy elsewhere.", 5000
        )

    def _reveal_in_explorer(self, path: str) -> None:
        # Passed as a raw command string (not a list) so Windows' argv-quoting
        # doesn't wrap "/select," together with the path — that breaks the
        # switch and explorer silently falls back to a default folder.
        norm = os.path.normpath(path)
        try:
            subprocess.run(f'explorer /select,"{norm}"')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open Explorer:\n{e}")

    # ── Video ─────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _open_current_video(self) -> None:
        path = self._current_path()
        if path and is_video(path):
            try:
                os.startfile(path)  # noqa — Windows-only app
            except OSError as e:
                QMessageBox.critical(self, "Cannot Play", f"Could not open video:\n{e}")

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def _on_image_selected(self, index: int) -> None:
        if self._compare_armed:
            self._compare_armed = False
            left = self._current_path()
            if left is not None and 0 <= index < len(self._image_paths) and index != self._current_index:
                right = self._image_paths[index]
                self._filmstrip.select_index(self._current_index)
                dialog = CompareDialog(left, right, self)
                dialog.exec()
                self.statusBar().clearMessage()
                return
        self._show_image(index)

    def _move_filmstrip_selection(self, delta: int) -> None:
        if not self._image_paths:
            return
        row = self._filmstrip.currentRow()
        row = 0 if row < 0 else max(0, min(row + delta, len(self._image_paths) - 1))
        self._filmstrip.select_index(row)

    def _navigate(self, delta: int) -> None:
        new_index = self._current_index + delta
        new_index = max(0, min(new_index, len(self._image_paths) - 1))
        if new_index != self._current_index:
            self._show_image(new_index)

    @pyqtSlot()
    def _on_thumbnails_done(self) -> None:
        self.statusBar().showMessage(
            f"Ready — {len(self._image_paths)} files loaded.", 5000
        )
        self._thumbnail_worker = None

    @pyqtSlot(str)
    def _on_worker_error(self, message: str) -> None:
        self.statusBar().showMessage(f"Thumbnail error: {message}")
        self._thumbnail_worker = None

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key.Key_Left:
            self._navigate(-1)
        elif key == Qt.Key.Key_Right:
            self._navigate(1)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Move the filmstrip highlight only; Space loads it into the viewer.
            self._move_filmstrip_selection(-1 if key == Qt.Key.Key_Up else 1)
        elif key == Qt.Key.Key_Space:
            row = self._filmstrip.currentRow()
            if row >= 0:
                self._on_image_selected(row)
        elif key == Qt.Key.Key_R:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                self._viewer.rotate(-90)   # rotate left
            else:
                self._viewer.rotate(90)    # rotate right
            self._update_edit_controls()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_5:
            self._set_rating(key - Qt.Key.Key_0)
        elif key == Qt.Key.Key_F:
            self._toggle_flag()
        elif key == Qt.Key.Key_Delete:
            self._delete_current()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._open_current_video()
        elif key == Qt.Key.Key_Escape:
            self._compare_armed = False
            self._cancel_edit_state()
            self.statusBar().clearMessage()
        else:
            super().keyPressEvent(event)

    # ── Slideshow ─────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _start_slideshow(self) -> None:
        stills = [p for p in self._image_paths if not is_video(p)]
        if not stills:
            self.statusBar().showMessage("No still images to show in a slideshow.", 5000)
            return
        current = self._current_path()
        start = stills.index(current) if current in stills else 0
        delay = max(0.5, self._delay_spin.value())
        self._slideshow_window = SlideshowWindow(
            image_paths=stills,
            start_index=start,
            delay_seconds=delay,
            fade_seconds=self._fade_spin.value(),
        )

    # ── Window Close ──────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            self._thumbnail_worker.cancel()
            self._thumbnail_worker.wait()
        if self._similarity_index_worker and self._similarity_index_worker.isRunning():
            self._similarity_index_worker.cancel()
            self._similarity_index_worker.wait()
        if self._similarity_search_worker and self._similarity_search_worker.isRunning():
            self._similarity_search_worker.cancel()
            self._similarity_search_worker.wait()
        self._similarity_cache.close()
        if self._slideshow_window:
            self._slideshow_window.close()
        self._save_config()
        event.accept()
