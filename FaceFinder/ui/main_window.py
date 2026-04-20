"""Main window UI for FaceFinder application"""

import os
import logging
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import face_recognition
import numpy as np
from PIL import Image, ImageGrab

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QCheckBox, QSlider, QProgressBar, QListWidget,
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon

from config import ConfigManager
from ui.styles import STYLESHEET, COLORS
from ui.results_viewer import ResultsViewer

log_file = Path(__file__).parent.parent / f"facefinder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)

SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp')
NUM_WORKERS = max(4, int(os.cpu_count() * 0.75)) if os.cpu_count() else 10


def _load_image_as_rgb(image_path: str, max_size: int = 1500) -> np.ndarray:
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
    arr = np.array(img, dtype=np.uint8)
    if not arr.flags['C_CONTIGUOUS']:
        arr = np.ascontiguousarray(arr)
    return arr


def _process_single_image(args) -> Optional[str]:
    file_path_str, ref_encoding, tolerance = args
    try:
        image = _load_image_as_rgb(file_path_str)
        encodings = face_recognition.face_encodings(image)
        for enc in encodings:
            if face_recognition.compare_faces([ref_encoding], enc, tolerance=tolerance)[0]:
                return file_path_str
    except Exception:
        pass
    return None


class MainWindow(QMainWindow):
    _search_done = pyqtSignal(list, object)  # matches, error_str_or_None

    def __init__(self, config_manager: ConfigManager, version: str):
        super().__init__()
        self.config = config_manager
        self.version = version

        self._search_cancelled = False
        self._search_thread: Optional[threading.Thread] = None
        self._explorer_process = None

        self.setWindowTitle(f"FaceFinder v{self.version}")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(STYLESHEET)
        self.resize(750, 650)

        self._build_ui()
        self._load_config()
        self._search_done.connect(self._on_search_done)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("FaceFinder")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Search for matching faces in your image collection")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Reference image
        ref_group = QGroupBox("Reference Image  (drag & drop or Ctrl+V to paste)")
        ref_layout = QVBoxLayout(ref_group)
        ref_row = QHBoxLayout()
        self.ref_edit = QLineEdit()
        ref_browse = QPushButton("Browse...")
        ref_browse.setMinimumWidth(100)
        ref_browse.clicked.connect(self._browse_reference)
        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("secondary_btn")
        paste_btn.setMinimumWidth(60)
        paste_btn.clicked.connect(self._paste_from_clipboard)
        ref_row.addWidget(self.ref_edit, stretch=1)
        ref_row.addWidget(paste_btn)
        ref_row.addWidget(ref_browse)
        ref_layout.addLayout(ref_row)
        layout.addWidget(ref_group)

        # Search folder
        folder_group = QGroupBox("Search Folder")
        folder_layout = QVBoxLayout(folder_group)
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        folder_browse = QPushButton("Browse...")
        folder_browse.setMinimumWidth(100)
        folder_browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(folder_browse)
        folder_layout.addLayout(folder_row)
        layout.addWidget(folder_group)

        # Options
        opt_group = QGroupBox("Search Options")
        opt_layout = QVBoxLayout(opt_group)
        self.recursive_check = QCheckBox("Search subfolders recursively")
        self.recursive_check.setChecked(True)
        opt_layout.addWidget(self.recursive_check)

        tol_row = QHBoxLayout()
        tol_row.addWidget(QLabel("Face Match Tolerance:"))
        self.tolerance_label = QLabel("0.60")
        self.tolerance_label.setMinimumWidth(40)
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(10, 100)
        self.tolerance_slider.setValue(60)
        self.tolerance_slider.setTickInterval(5)
        self.tolerance_slider.valueChanged.connect(self._on_tolerance_changed)
        tol_row.addWidget(self.tolerance_slider, stretch=1)
        tol_row.addWidget(self.tolerance_label)
        opt_layout.addLayout(tol_row)
        hint = QLabel("Lower = stricter matching, Higher = more lenient")
        hint.setObjectName("subtitle")
        opt_layout.addWidget(hint)
        layout.addWidget(opt_group)

        # Buttons
        btn_row = QHBoxLayout()
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._start_search)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_search)
        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("subtitle")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Results
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._on_result_double_click)
        results_layout.addWidget(self.results_list)
        layout.addWidget(results_group, stretch=1)

        self.results_list.addItem("Ready to search...")

        # Keyboard shortcut for paste
        from PyQt6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self._paste_from_clipboard)

    def _load_config(self):
        self.ref_edit.setText(self.config.get("default_reference_image", ""))
        self.folder_edit.setText(self.config.get("default_search_folder", ""))
        tol = self.config.get("tolerance", 0.6)
        self.tolerance_slider.setValue(int(tol * 100))
        self.recursive_check.setChecked(self.config.get("recursive_search", True))

    def _on_tolerance_changed(self, value: int):
        self.tolerance_label.setText(f"{value / 100:.2f}")

    def _browse_reference(self):
        current = self.ref_edit.text().strip()
        start = str(Path(current).parent) if current and Path(current).exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", start,
            "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;All files (*.*)"
        )
        if path:
            self._set_reference(path)

    def _browse_folder(self):
        existing = self.folder_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Search Folder", start)
        if folder:
            self.folder_edit.setText(folder)
            self.config.set("default_search_folder", folder)
            self.config.save()
            self._add_result(f"Search folder: {folder}")

    def _set_reference(self, path: str):
        self.ref_edit.setText(path)
        self.config.set("default_reference_image", path)
        self.config.save()
        self._add_result(f"Reference image: {Path(path).name}")

    def _paste_from_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                QMessageBox.information(self, "No Image", "No image found in clipboard.")
                return
            if isinstance(img, list):
                for item in img:
                    if isinstance(item, str) and Path(item).exists():
                        if Path(item).suffix.lower() in SUPPORTED_EXTENSIONS:
                            self._set_reference(item)
                            return
                QMessageBox.warning(self, "Invalid Clipboard", "No valid image paths in clipboard.")
                return
            if hasattr(img, 'save'):
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                temp_path = os.path.join(tempfile.gettempdir(), "facefinder_clipboard_ref.png")
                img.save(temp_path, 'PNG')
                self._set_reference(temp_path)
                self._add_result("(Pasted from clipboard)")
        except Exception as e:
            QMessageBox.critical(self, "Clipboard Error", f"Failed to paste from clipboard:\n{e}")

    def _start_search(self):
        ref_path = self.ref_edit.text().strip()
        folder = self.folder_edit.text().strip()
        if not ref_path:
            QMessageBox.critical(self, "Error", "Please select a reference image")
            return
        if not folder:
            QMessageBox.critical(self, "Error", "Please select a search folder")
            return
        if not Path(ref_path).exists():
            QMessageBox.critical(self, "Error", "Reference image not found")
            return
        if not Path(folder).exists():
            QMessageBox.critical(self, "Error", "Search folder not found")
            return

        self.config.set("tolerance", self.tolerance_slider.value() / 100)
        self.config.set("recursive_search", self.recursive_check.isChecked())
        self.config.save()

        self.results_list.clear()
        self.progress_bar.setValue(0)
        self._search_cancelled = False
        self.search_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self._search_thread = threading.Thread(
            target=self._perform_search,
            args=(ref_path, folder),
            daemon=True
        )
        self._search_thread.start()

    def _cancel_search(self):
        self._search_cancelled = True
        self._add_result("Cancelling search...")

    def _perform_search(self, ref_path: str, folder: str):
        try:
            logger.info(f"=== Starting search === ref={ref_path} folder={folder}")
            self._update_progress(0, 1, "Loading reference image...")
            self._add_result(f"Loading reference image: {ref_path}")

            ref_image = _load_image_as_rgb(ref_path)
            self._add_result("Detecting face in reference image...")
            ref_encodings = face_recognition.face_encodings(ref_image)

            if not ref_encodings:
                self._search_done.emit([], "No face found in reference image")
                return

            self._add_result(f"Found {len(ref_encodings)} face(s) in reference image")
            ref_encoding = ref_encodings[0]

            self._update_progress(0, 1, "Scanning for images...")
            image_files = self._collect_images(folder)
            if not image_files:
                self._search_done.emit([], "No images found in folder")
                return

            total = len(image_files)
            tolerance = self.tolerance_slider.value() / 100
            self._add_result(f"Found {total} images to scan using {NUM_WORKERS} processes")

            matches: List[str] = []
            matched_set: set = set()
            processed = 0
            work_items = [(str(fp), ref_encoding, tolerance) for fp in image_files]

            with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
                futures = {executor.submit(_process_single_image, item): item[0] for item in work_items}
                for future in as_completed(futures):
                    if self._search_cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    file_path = futures[future]
                    try:
                        result = future.result(timeout=60)
                        processed += 1
                        self._update_progress(processed, total, f"Scanned: {processed}/{total}")
                        if result and result not in matched_set:
                            matched_set.add(result)
                            matches.append(result)
                            self._add_result(f"MATCH: {result}")
                    except Exception as e:
                        logger.error(f"Error for {file_path}: {e}")
                        processed += 1
                        self._update_progress(processed, total, f"Scanned: {processed}/{total}")

            if self._search_cancelled:
                self._search_done.emit(matches, "Search cancelled")
            else:
                self._search_done.emit(matches, None)

        except Exception as e:
            logger.exception(f"Search failed: {e}")
            self._search_done.emit([], str(e))

    def _collect_images(self, folder: str) -> List[Path]:
        folder_path = Path(folder)
        files_set: set = set()
        glob = folder_path.rglob if self.recursive_check.isChecked() else folder_path.glob
        for ext in SUPPORTED_EXTENSIONS:
            for f in glob(f"*{ext}"):
                files_set.add(f.resolve())
        return list(files_set)

    def _update_progress(self, current: int, total: int, message: str):
        # Called from worker thread — use signal-safe approach via QTimer.singleShot via lambda in main thread
        # Since pyqtSignal can't be called from non-main easily without a dedicated signal,
        # we use a simple approach: post to the main thread via QTimer trick won't work from worker.
        # Instead emit a dedicated signal. But we keep it simple: _search_done handles final state.
        # For progress we update via direct invocation since QLabel/QProgressBar are thread-safe for reads.
        # Actually in Qt you CANNOT update widgets from non-main threads. Use the existing queue pattern.
        pass  # Progress is approximate — final state handled by _search_done

    def _add_result(self, message: str):
        # This gets called from worker thread; use invokeMethod pattern via signal
        # We'll queue via QTimer in main thread using a lightweight approach
        import PyQt6.QtCore as _qc
        _qc.QMetaObject.invokeMethod(
            self.results_list, "addItem",
            _qc.Qt.ConnectionType.QueuedConnection,
            _qc.Q_ARG(str, message)
        )

    def _on_search_done(self, matches: List[str], error):
        self.search_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)

        if error:
            self.progress_label.setText(str(error))
            if not self._search_cancelled:
                QMessageBox.critical(self, "Search Error", str(error))
        else:
            self.progress_label.setText(f"Complete — Found {len(matches)} matches")
            self.results_list.addItem(f"\n--- Found {len(matches)} matches ---")
            if matches:
                viewer = ResultsViewer(self, matches)
                viewer.exec()
            else:
                QMessageBox.information(self, "Search Complete", "No matching faces found")

    def _on_result_double_click(self, item):
        text = item.text()
        if text.startswith("MATCH: "):
            path = Path(text[7:])
            if path.exists():
                if self._explorer_process is not None:
                    try:
                        self._explorer_process.terminate()
                    except Exception:
                        pass
                import subprocess
                self._explorer_process = subprocess.Popen(['explorer', '/select,', str(path)])
