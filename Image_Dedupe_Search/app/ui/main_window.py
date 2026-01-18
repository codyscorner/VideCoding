"""Main application window for Image Dedupe Search"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QProgressBar,
    QFileDialog, QMessageBox, QFrame, QApplication, QGroupBox
)
from PySide6.QtCore import Qt, Slot
from typing import Optional, List, Dict
import numpy as np

from config import ConfigManager
from app.ui.styles import ThemeManager
from app.ui.thumbnail_view import ThumbnailView
from app.ui.image_compare_dialog import ImageCompareDialog
from app.ui.search_by_image_dialog import SearchByImageDialog
from app.ui.settings_dialog import SettingsDialog
from app.core.cache import EmbeddingCache
from app.core.image_utils import ImageMetadata, ImageUtils, SUPPORTED_EXTENSIONS
from app.core.similarity import DuplicateGroup, SimilarityEngine
from app.core.embeddings import EmbeddingEngine
from app.workers.scan_worker import ScanWorker
from app.workers.embed_worker import EmbedWorker
from app.workers.similarity_worker import SimilarityWorker


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, config_manager: ConfigManager, version: str):
        """
        Initialize main window

        Args:
            config_manager: Configuration manager instance
            version: Application version string
        """
        super().__init__()
        self.config = config_manager
        self.version = version
        self.theme = ThemeManager('dark_blue')

        # State
        self.current_folder: Optional[str] = None
        self.scanned_images: List[ImageMetadata] = []
        self.embeddings: Dict[str, np.ndarray] = {}
        self.duplicate_groups: List[DuplicateGroup] = []
        self.current_group_index: int = 0

        # Search by image state
        self.search_image_path: Optional[str] = None
        self.search_results: List[tuple] = []  # List of (path, score)

        # Workers
        self._scan_worker: Optional[ScanWorker] = None
        self._embed_worker: Optional[EmbedWorker] = None
        self._similarity_worker: Optional[SimilarityWorker] = None

        # Cache
        self._cache: Optional[EmbeddingCache] = None
        self._init_cache()

        self._setup_ui()
        self._connect_signals()
        self._load_from_config()
        self._apply_theme()

    def _init_cache(self) -> None:
        """Initialize embedding cache"""
        cache_path = self.config.get("cache_path", "./data/cache.sqlite")
        self._cache = EmbeddingCache(cache_path)
        self._cache.connect()

    def _setup_ui(self) -> None:
        """Build the UI"""
        self.setWindowTitle(f"Image Dedupe Search v{self.version}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Folder selection section
        self._create_folder_section(layout)

        # Search by image section
        self._create_search_image_section(layout)

        # Threshold section
        self._create_threshold_section(layout)

        # Progress section
        self._create_progress_section(layout)

        # Thumbnail view
        self._create_thumbnail_section(layout)

        # Navigation section
        self._create_navigation_section(layout)

    def _create_folder_section(self, parent_layout: QVBoxLayout) -> None:
        """Create folder picker section"""
        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Folder:")
        label.setFixedWidth(60)
        layout.addWidget(label)

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select a folder to scan for images...")
        self.folder_input.setReadOnly(True)
        layout.addWidget(self.folder_input)

        self.browse_btn = QPushButton("...")
        self.browse_btn.setProperty("cssClass", "browse")
        self.browse_btn.setFixedWidth(40)
        self.browse_btn.clicked.connect(self._browse_folder)
        layout.addWidget(self.browse_btn)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setFixedWidth(80)
        self.scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self.scan_btn)

        parent_layout.addWidget(section)

    def _create_search_image_section(self, parent_layout: QVBoxLayout) -> None:
        """Create search by image button section"""
        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addStretch()

        self.search_by_image_btn = QPushButton("Search by Image...")
        self.search_by_image_btn.setFixedWidth(180)
        self.search_by_image_btn.setToolTip("Find similar images to a reference image")
        self.search_by_image_btn.clicked.connect(self._open_search_by_image)
        layout.addWidget(self.search_by_image_btn)

        layout.addStretch()

        parent_layout.addWidget(section)

    @Slot()
    def _open_search_by_image(self) -> None:
        """Open the Search by Image dialog"""
        dialog = SearchByImageDialog(
            config=self.config._config,
            cache=self._cache,
            parent=self,
            theme=self.theme
        )
        dialog.exec()

    @Slot()
    def _open_settings(self) -> None:
        """Open the Settings dialog"""
        dialog = SettingsDialog(
            config=self.config._config,
            parent=self,
            theme=self.theme
        )
        if dialog.exec() and dialog.changes_made():
            # Save config after settings change
            self.config.save()

            # Update thumbnail size if changed
            new_thumb_size = self.config.get("thumbnail_size", 150)
            self.thumbnail_view.set_thumbnail_size(new_thumb_size)

    def _create_threshold_section(self, parent_layout: QVBoxLayout) -> None:
        """Create similarity threshold section"""
        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Threshold:")
        label.setFixedWidth(70)
        layout.addWidget(label)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(80)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(92)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(5)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("0.92")
        self.threshold_label.setFixedWidth(40)
        layout.addWidget(self.threshold_label)

        # Re-scan button to apply new threshold
        self.rescan_btn = QPushButton("Re-scan")
        self.rescan_btn.setFixedWidth(100)
        self.rescan_btn.setEnabled(False)
        self.rescan_btn.setToolTip("Re-find duplicates with current threshold")
        self.rescan_btn.clicked.connect(self._find_duplicates)
        layout.addWidget(self.rescan_btn)

        parent_layout.addWidget(section)

    def _create_progress_section(self, parent_layout: QVBoxLayout) -> None:
        """Create progress and status section"""
        section = QFrame()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setProperty("cssClass", "status")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        parent_layout.addWidget(section)

    def _create_thumbnail_section(self, parent_layout: QVBoxLayout) -> None:
        """Create thumbnail grid section"""
        self.thumbnail_view = ThumbnailView(
            thumbnail_size=self.config.get("thumbnail_size", 150)
        )
        self.thumbnail_view.image_double_clicked.connect(self._on_image_double_clicked)
        parent_layout.addWidget(self.thumbnail_view, 1)

    def _create_navigation_section(self, parent_layout: QVBoxLayout) -> None:
        """Create group navigation section"""
        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        self.group_label = QLabel("No groups")
        layout.addWidget(self.group_label)

        layout.addStretch()

        self.prev_group_btn = QPushButton("Previous Group")
        self.prev_group_btn.setEnabled(False)
        self.prev_group_btn.clicked.connect(self._show_prev_group)
        layout.addWidget(self.prev_group_btn)

        self.next_group_btn = QPushButton("Next Group")
        self.next_group_btn.setEnabled(False)
        self.next_group_btn.clicked.connect(self._show_next_group)
        layout.addWidget(self.next_group_btn)

        layout.addStretch()

        self.compare_btn = QPushButton("Compare Selected")
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self._show_comparison)
        layout.addWidget(self.compare_btn)

        # Settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setFixedWidth(100)
        self.settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self.settings_btn)

        parent_layout.addWidget(section)

    def _connect_signals(self) -> None:
        """Connect additional signals"""
        pass

    def _load_from_config(self) -> None:
        """Load settings from config"""
        # Set threshold from config
        threshold = self.config.get("similarity_threshold", 0.92)
        self.threshold_slider.setValue(int(threshold * 100))

        # Set last folder if available
        last_folder = self.config.get("last_scan_folder", "")
        if last_folder:
            self.folder_input.setText(last_folder)
            self.current_folder = last_folder

    def _apply_theme(self) -> None:
        """Apply theme stylesheet"""
        self.setStyleSheet(self.theme.get_stylesheet())

    @Slot()
    def _browse_folder(self) -> None:
        """Open folder browser dialog"""
        start_dir = self.current_folder or ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Scan",
            start_dir
        )

        if folder:
            self.folder_input.setText(folder)
            self.current_folder = folder
            self.config.set("last_scan_folder", folder)
            self.config.save()

    @Slot()
    def _start_scan(self) -> None:
        """Start directory scan"""
        if not self.current_folder:
            QMessageBox.warning(
                self,
                "No Folder Selected",
                "Please select a folder to scan."
            )
            return

        # Reset state
        self.scanned_images.clear()
        self.embeddings.clear()
        self.duplicate_groups.clear()
        self.thumbnail_view.clear_thumbnails()
        self._update_group_navigation()

        # Disable controls
        self._set_controls_enabled(False)

        # Get settings
        min_res = self.config.get("min_resolution", [256, 256])
        min_resolution = tuple(min_res) if min_res else None
        recursive = self.config.get("recursive_scan", True)
        excluded = self.config.get("excluded_dirs", [])

        # Start scan worker
        self._scan_worker = ScanWorker(
            directory=self.current_folder,
            recursive=recursive,
            excluded_dirs=excluded,
            min_resolution=min_resolution
        )
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_error)
        self._scan_worker.start()

        self.status_label.setText("Scanning for images...")

    @Slot(int, int, str)
    def _on_scan_progress(self, current: int, total: int, filename: str) -> None:
        """Handle scan progress"""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            self.status_label.setText(f"Scanning: {filename}")
        else:
            self.progress_bar.setMaximum(0)
            self.status_label.setText("Counting files...")

    @Slot(list)
    def _on_scan_finished(self, images: list) -> None:
        """Handle scan completion"""
        self.scanned_images = images
        self._scan_worker = None

        if not images:
            self.status_label.setText("No images found")
            self._set_controls_enabled(True)
            return

        self.status_label.setText(f"Found {len(images)} images. Computing embeddings...")
        self.progress_bar.setValue(0)

        # Start embedding computation
        self._start_embedding()

    def _start_embedding(self) -> None:
        """Start embedding computation"""
        image_paths = [img.path for img in self.scanned_images]

        self._embed_worker = EmbedWorker(
            image_paths=image_paths,
            model_name=self.config.get("model_name", "clip-ViT-B-32"),
            cache=self._cache,
            batch_size=self.config.get("batch_size", 512),
            use_gpu=self.config.get("use_gpu", True),
            io_workers=self.config.get("io_workers", 12)
        )
        self._embed_worker.progress.connect(self._on_embed_progress)
        self._embed_worker.status.connect(self._on_embed_status)
        self._embed_worker.model_loading.connect(self._on_model_loading)
        self._embed_worker.model_loaded.connect(self._on_model_loaded)
        self._embed_worker.finished.connect(self._on_embed_finished)
        self._embed_worker.error.connect(self._on_error)
        self._embed_worker.start()

    @Slot(int, int, str)
    def _on_embed_progress(self, current: int, total: int, message: str) -> None:
        """Handle embedding progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    @Slot(str)
    def _on_embed_status(self, message: str) -> None:
        """Handle embedding status update"""
        self.status_label.setText(message)

    @Slot()
    def _on_model_loading(self) -> None:
        """Handle model loading start"""
        self.status_label.setText("Loading CLIP model (this may take a moment)...")
        self.progress_bar.setMaximum(0)  # Indeterminate
        QApplication.processEvents()

    @Slot()
    def _on_model_loaded(self) -> None:
        """Handle model loaded"""
        self.status_label.setText("Model loaded, computing embeddings...")

    @Slot(dict)
    def _on_embed_finished(self, embeddings: dict) -> None:
        """Handle embedding completion"""
        self.embeddings = embeddings
        self._embed_worker = None

        successful = sum(1 for e in embeddings.values() if e is not None)
        self.status_label.setText(f"Computed {successful} embeddings. Finding duplicates...")
        self.progress_bar.setValue(self.progress_bar.maximum())

        # Automatically proceed to find duplicates
        self._find_duplicates()

    @Slot()
    def _find_duplicates(self) -> None:
        """Start similarity search"""
        if not self.embeddings:
            QMessageBox.warning(
                self,
                "No Embeddings",
                "Please scan a folder first."
            )
            return

        # Filter out None embeddings
        valid_embeddings = {
            k: v for k, v in self.embeddings.items()
            if v is not None
        }

        if len(valid_embeddings) < 2:
            QMessageBox.information(
                self,
                "Not Enough Images",
                "Need at least 2 images with valid embeddings to find duplicates."
            )
            return

        # Build metadata dict
        metadata = {}
        for img in self.scanned_images:
            metadata[img.path] = {
                'width': img.width,
                'height': img.height,
                'file_size': img.file_size
            }

        # Disable controls
        self._set_controls_enabled(False)

        # Get threshold
        threshold = self.threshold_slider.value() / 100.0

        # Start similarity worker
        self._similarity_worker = SimilarityWorker(
            embeddings=valid_embeddings,
            image_metadata=metadata,
            threshold=threshold
        )
        self._similarity_worker.progress.connect(self._on_similarity_progress)
        self._similarity_worker.status.connect(self._on_similarity_status)
        self._similarity_worker.finished.connect(self._on_similarity_finished)
        self._similarity_worker.error.connect(self._on_error)
        self._similarity_worker.start()

        self.status_label.setText("Computing similarities...")
        self.progress_bar.setValue(0)

    @Slot(int, int)
    def _on_similarity_progress(self, current: int, total: int) -> None:
        """Handle similarity progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    @Slot(str)
    def _on_similarity_status(self, message: str) -> None:
        """Handle similarity status"""
        self.status_label.setText(message)

    @Slot(list)
    def _on_similarity_finished(self, groups: list) -> None:
        """Handle similarity completion"""
        self.duplicate_groups = groups
        self._similarity_worker = None

        self._set_controls_enabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())

        if not groups:
            self.status_label.setText("No duplicates found at current threshold.")
            self.thumbnail_view.clear_thumbnails()
            self._update_group_navigation()
            return

        total_dupes = sum(len(g.duplicates) for g in groups)
        self.status_label.setText(
            f"Found {len(groups)} groups with {total_dupes} duplicates. "
            "Double-click an image to compare."
        )

        # Show first group
        self.current_group_index = 0
        self._display_current_group()

    def _display_current_group(self) -> None:
        """Display the current duplicate group"""
        if not self.duplicate_groups:
            self.thumbnail_view.clear_thumbnails()
            self._update_group_navigation()
            return

        group = self.duplicate_groups[self.current_group_index]

        # Build similarity dict for display
        similarities = {group.representative: 1.0}
        similarities.update(group.similarity_scores)

        # Show all images in group
        self.thumbnail_view.set_images(
            group.all_images,
            similarities=similarities,
            representative=group.representative
        )

        self._update_group_navigation()

    def _update_group_navigation(self) -> None:
        """Update group navigation controls"""
        total = len(self.duplicate_groups)

        if total == 0:
            self.group_label.setText("No groups")
            self.prev_group_btn.setEnabled(False)
            self.next_group_btn.setEnabled(False)
            self.compare_btn.setEnabled(False)
        else:
            self.group_label.setText(
                f"Group {self.current_group_index + 1} of {total}"
            )
            self.prev_group_btn.setEnabled(self.current_group_index > 0)
            self.next_group_btn.setEnabled(self.current_group_index < total - 1)
            self.compare_btn.setEnabled(True)

    @Slot()
    def _show_prev_group(self) -> None:
        """Show previous duplicate group"""
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self._display_current_group()

    @Slot()
    def _show_next_group(self) -> None:
        """Show next duplicate group"""
        if self.current_group_index < len(self.duplicate_groups) - 1:
            self.current_group_index += 1
            self._display_current_group()

    @Slot(str)
    def _on_image_double_clicked(self, path: str) -> None:
        """Handle image double-click"""
        self._show_comparison()

    @Slot()
    def _show_comparison(self) -> None:
        """Show comparison dialog for current group"""
        if not self.duplicate_groups:
            return

        group = self.duplicate_groups[self.current_group_index]

        if not group.duplicates:
            QMessageBox.information(
                self,
                "No Duplicates",
                "No duplicates remaining in this group."
            )
            return

        dialog = ImageCompareDialog(
            group=group,
            parent=self,
            theme=self.theme
        )
        dialog.group_updated.connect(self._on_group_updated)
        dialog.exec()

    @Slot()
    def _on_group_updated(self) -> None:
        """Handle group update from comparison dialog"""
        # Refresh display
        self._display_current_group()

        # Remove empty groups
        self.duplicate_groups = [
            g for g in self.duplicate_groups
            if g.duplicates
        ]

        # Adjust index if needed
        if self.current_group_index >= len(self.duplicate_groups):
            self.current_group_index = max(0, len(self.duplicate_groups) - 1)

        self._update_group_navigation()

        if self.duplicate_groups:
            self._display_current_group()
        else:
            self.thumbnail_view.clear_thumbnails()
            self.status_label.setText("All duplicates have been processed.")

    @Slot(int)
    def _on_threshold_changed(self, value: int) -> None:
        """Handle threshold slider change"""
        threshold = value / 100.0
        self.threshold_label.setText(f"{threshold:.2f}")
        self.config.set("similarity_threshold", threshold)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        """Handle worker error"""
        self._set_controls_enabled(True)
        self.status_label.setText(f"Error: {message}")
        QMessageBox.critical(self, "Error", message)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable controls during processing"""
        self.scan_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.rescan_btn.setEnabled(enabled and bool(self.embeddings))
        self.threshold_slider.setEnabled(enabled)

    def closeEvent(self, event) -> None:
        """Handle window close"""
        # Cancel any running workers
        if self._scan_worker:
            self._scan_worker.cancel()
            self._scan_worker.wait()

        if self._embed_worker:
            self._embed_worker.cancel()
            self._embed_worker.wait()

        if self._similarity_worker:
            self._similarity_worker.cancel()
            self._similarity_worker.wait()

        # Close cache
        if self._cache:
            self._cache.close()

        # Save config
        self.config.save()

        event.accept()
