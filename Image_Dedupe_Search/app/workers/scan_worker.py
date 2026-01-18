"""Worker thread for scanning directories for images"""

from PySide6.QtCore import QThread, Signal
from typing import List, Optional, Tuple
from pathlib import Path
import os

from app.core.image_utils import ImageUtils, ImageMetadata, SUPPORTED_EXTENSIONS


class ScanWorker(QThread):
    """Worker thread for scanning directories for images"""

    # Signals
    progress = Signal(int, int, str)  # current, total, current_file
    finished = Signal(list)  # List[ImageMetadata]
    error = Signal(str)  # Error message

    def __init__(
        self,
        directory: str,
        recursive: bool = True,
        excluded_dirs: Optional[List[str]] = None,
        min_resolution: Optional[Tuple[int, int]] = None,
        parent=None
    ):
        """
        Initialize scan worker

        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            excluded_dirs: List of directory names to exclude
            min_resolution: Optional minimum resolution (width, height)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.directory = directory
        self.recursive = recursive
        self.excluded_dirs = set(excluded_dirs or [])
        self.min_resolution = min_resolution
        self._is_cancelled = False

    def run(self) -> None:
        """
        Scan directory and emit results

        Emits progress during scan and finished with list of ImageMetadata.
        """
        try:
            # First pass: count files to determine total
            self.progress.emit(0, 0, "Counting files...")

            image_files = self._find_image_files()

            if self._is_cancelled:
                return

            total = len(image_files)
            if total == 0:
                self.finished.emit([])
                return

            # Second pass: get metadata for each image
            results: List[ImageMetadata] = []
            processed = 0

            for file_path in image_files:
                if self._is_cancelled:
                    return

                # Apply resolution filter if specified
                if self.min_resolution:
                    if not ImageUtils.meets_resolution_filter(file_path, self.min_resolution):
                        processed += 1
                        continue

                # Get metadata
                metadata = ImageUtils.get_image_metadata(file_path)
                if metadata:
                    results.append(metadata)

                processed += 1
                if processed % 10 == 0 or processed == total:
                    filename = Path(file_path).name
                    self.progress.emit(processed, total, filename)

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))

    def _find_image_files(self) -> List[str]:
        """Find all image files in directory"""
        image_files = []
        directory_path = Path(self.directory)

        if not directory_path.exists() or not directory_path.is_dir():
            return []

        if self.recursive:
            for root, dirs, files in os.walk(directory_path):
                if self._is_cancelled:
                    return []

                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

                for file in files:
                    if self._is_cancelled:
                        return []

                    ext = Path(file).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        file_path = os.path.join(root, file)
                        image_files.append(str(Path(file_path).absolute()))
        else:
            for file in directory_path.iterdir():
                if self._is_cancelled:
                    return []

                if file.is_file():
                    ext = file.suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        image_files.append(str(file.absolute()))

        return sorted(image_files)

    def cancel(self) -> None:
        """Request cancellation of the scan"""
        self._is_cancelled = True
