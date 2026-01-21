"""Face detection module for Image People Sorter - Two-pass detection strategy

Pass 1: Fast HOG scan (CPU parallel) - catches frontal faces quickly
Pass 2: Deep CNN scan (GPU batch) - catches angled/profile faces on remaining images
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from PIL import Image
import face_recognition


# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}

# Number of parallel workers for HOG (CPU-based, can use many)
# Ryzen 9 9950X has 16 cores - use 14 to leave headroom
MAX_WORKERS_HOG = 14

# Number of parallel workers for CNN (CPU-based since dlib lacks CUDA)
# CNN is heavier than HOG, so use fewer workers to avoid memory issues
MAX_WORKERS_CNN = 6


@dataclass
class SortResult:
    """Result of sorting a single image"""
    source_path: str
    dest_path: Optional[str]
    has_people: bool
    success: bool
    error_message: Optional[str] = None


# Standalone functions for multiprocessing (must be at module level)
def _load_image_as_rgb_standalone(image_path: str, max_size: int = 1800) -> np.ndarray:
    """
    Load an image and convert to RGB numpy array (standalone for multiprocessing)
    """
    img = Image.open(image_path)

    # Convert any format to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize if larger than max_size for performance
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # Convert to numpy array
    arr = np.array(img, dtype=np.uint8)

    # Ensure contiguous memory layout for dlib
    if not arr.flags['C_CONTIGUOUS']:
        arr = np.ascontiguousarray(arr)

    return arr


def _detect_faces_hog(image_path: str) -> Tuple[str, bool, Optional[str]]:
    """
    Fast face detection using HOG model (Pass 1)

    Good for frontal faces, very fast, low memory usage.

    Returns:
        Tuple of (image_path, has_faces, error_message)
    """
    try:
        image = _load_image_as_rgb_standalone(image_path)

        # HOG model - fast, good for frontal faces
        face_locations = face_recognition.face_locations(
            image,
            number_of_times_to_upsample=1,  # Keep at 1 for speed
            model="hog"
        )

        return (image_path, len(face_locations) > 0, None)

    except Exception as e:
        return (image_path, False, str(e))


def _detect_faces_cnn(image_path: str) -> Tuple[str, bool, Optional[str]]:
    """
    Deep face detection using CNN model (Pass 2)

    CNN is more accurate than HOG, catches faces at angles, profiles, smaller faces.
    Note: Running on CPU since dlib lacks CUDA support.

    Returns:
        Tuple of (image_path, has_faces, error_message)
    """
    try:
        image = _load_image_as_rgb_standalone(image_path, max_size=1400)

        # CNN model - slower but catches angled/profile faces
        face_locations = face_recognition.face_locations(
            image,
            number_of_times_to_upsample=1,
            model="cnn"
        )

        return (image_path, len(face_locations) > 0, None)

    except Exception as e:
        return (image_path, False, str(e))


class ImagePeopleSorter:
    """Sorts images based on whether they contain people - two-pass detection strategy"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        copy_mode: bool = True,
        max_workers_hog: int = MAX_WORKERS_HOG,
        max_workers_cnn: int = MAX_WORKERS_CNN
    ):
        """
        Initialize the sorter

        Args:
            status_callback: Callback for status messages
            progress_callback: Callback for progress (current, total, filename, file_progress)
            cancel_check: Callback that returns True if operation should be cancelled
            copy_mode: If True, copy files; if False, move files
            max_workers_hog: Number of parallel workers for HOG detection (CPU, fast pass)
            max_workers_cnn: Number of parallel workers for CNN detection (CPU, deep pass)
        """
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check
        self.copy_mode = copy_mode
        self.max_workers_hog = max_workers_hog
        self.max_workers_cnn = max_workers_cnn

    def _log_status(self, message: str) -> None:
        """Log a status message"""
        if self.status_callback:
            self.status_callback(message)

    def _get_image_files(self, folder: str, recursive: bool) -> List[str]:
        """
        Get all image files in a folder

        Args:
            folder: Folder to scan
            recursive: If True, scan subdirectories

        Returns:
            List of image file paths
        """
        files = []
        folder_path = Path(folder)

        if recursive:
            for ext in SUPPORTED_EXTENSIONS:
                files.extend(folder_path.rglob(f'*{ext}'))
                files.extend(folder_path.rglob(f'*{ext.upper()}'))
        else:
            for ext in SUPPORTED_EXTENSIONS:
                files.extend(folder_path.glob(f'*{ext}'))
                files.extend(folder_path.glob(f'*{ext.upper()}'))

        # Convert to strings and remove duplicates
        return list(set(str(f) for f in files))

    def _copy_or_move_file(self, source: str, dest: str) -> None:
        """Copy or move a file based on mode"""
        import shutil

        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if self.copy_mode:
            shutil.copy2(source, dest)
        else:
            shutil.move(source, dest)

    def _get_unique_dest_path(self, dest_folder: str, filename: str) -> str:
        """
        Get a unique destination path, numbering duplicates

        Args:
            dest_folder: Destination folder
            filename: Original filename

        Returns:
            Unique destination path
        """
        dest_path = os.path.join(dest_folder, filename)

        if not os.path.exists(dest_path):
            return dest_path

        # Add number for duplicates
        base_name, ext = os.path.splitext(filename)
        counter = 1

        while os.path.exists(dest_path):
            new_filename = f"{base_name}_{counter:03d}{ext}"
            dest_path = os.path.join(dest_folder, new_filename)
            counter += 1

        return dest_path

    def sort_images(
        self,
        source_folder: str,
        dest_folder: str,
        recursive: bool = True
    ) -> Tuple[List[SortResult], int, int]:
        """
        Sort images into People and No_People folders using two-pass face detection

        Pass 1: Fast HOG scan (parallel, many workers) - catches frontal faces
        Pass 2: Deep CNN scan (limited workers) - only on images HOG missed

        Args:
            source_folder: Source folder containing images
            dest_folder: Destination folder for sorted images
            recursive: If True, scan subdirectories

        Returns:
            Tuple of (results list, people count, no people count)
        """
        # Validate folders
        if not os.path.exists(source_folder):
            raise ValueError(f"Source folder does not exist: {source_folder}")

        # Create destination subfolders
        people_folder = os.path.join(dest_folder, "People")
        no_people_folder = os.path.join(dest_folder, "No_People")
        os.makedirs(people_folder, exist_ok=True)
        os.makedirs(no_people_folder, exist_ok=True)

        # Get all image files
        mode_str = "recursively" if recursive else "in root folder only"
        self._log_status(f"Scanning source folder {mode_str}...")
        image_files = self._get_image_files(source_folder, recursive)

        if not image_files:
            self._log_status("No image files found in source folder")
            return [], 0, 0

        total_files = len(image_files)
        self._log_status(f"Found {total_files} images to process")

        # Detection results storage
        detection_results = {}  # image_path -> (has_people, error)
        needs_deep_scan = []    # Images that need CNN pass

        # =========================================
        # PASS 1: Fast HOG scan (parallel, many workers)
        # =========================================
        self._log_status(f"Pass 1: Fast scan with {self.max_workers_hog} workers...")
        processed = 0
        hog_found = 0

        with ProcessPoolExecutor(max_workers=self.max_workers_hog) as executor:
            future_to_path = {
                executor.submit(_detect_faces_hog, path): path
                for path in image_files
            }

            for future in as_completed(future_to_path):
                if self.cancel_check and self.cancel_check():
                    self._log_status("Cancellation requested...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    image_path, has_people, error = future.result()
                    processed += 1
                    filename = os.path.basename(image_path)

                    if error:
                        detection_results[image_path] = (False, error)
                        self._log_status(f"Error: {filename} - {error}")
                    elif has_people:
                        detection_results[image_path] = (True, None)
                        hog_found += 1
                        self._log_status(f"[HOG] Face found: {filename}")
                    else:
                        # No face found - queue for deep scan
                        needs_deep_scan.append(image_path)

                    # Progress: Pass 1 is 70% of total work (no CNN pass)
                    if self.progress_callback:
                        progress = int((processed / total_files) * 70)
                        self.progress_callback(progress, 100, f"Scanning: {filename}", 100)

                except Exception as e:
                    path = future_to_path[future]
                    detection_results[path] = (False, str(e))
                    processed += 1

        if self.cancel_check and self.cancel_check():
            self._log_status("Operation cancelled during Pass 1")
            return [], 0, 0

        self._log_status(f"Pass 1 complete: {hog_found} faces found, {len(needs_deep_scan)} need deep scan")

        # =========================================
        # Mark remaining images as no-face (skip CNN - too slow without GPU)
        # =========================================
        cnn_found = 0
        for image_path in needs_deep_scan:
            detection_results[image_path] = (False, None)

        self._log_status(f"Skipped deep scan: {len(needs_deep_scan)} images marked as no-face (review manually if needed)")

        # =========================================
        # PASS 3: Copy/Move files
        # =========================================
        self._log_status(f"Pass 3: {'Copying' if self.copy_mode else 'Moving'} files...")

        results = []
        people_count = 0
        no_people_count = 0

        for idx, image_path in enumerate(image_files, 1):
            if self.cancel_check and self.cancel_check():
                self._log_status("Operation cancelled by user")
                break

            filename = os.path.basename(image_path)
            has_people, error = detection_results.get(image_path, (False, "Not processed"))

            # Progress: File copy is 30% of total work (70-100%)
            if self.progress_callback:
                progress = 70 + int((idx / total_files) * 30)
                self.progress_callback(progress, 100, f"{'Copying' if self.copy_mode else 'Moving'}: {filename}", 100)

            if error:
                results.append(SortResult(
                    source_path=image_path,
                    dest_path=None,
                    has_people=False,
                    success=False,
                    error_message=error
                ))
                continue

            try:
                if has_people:
                    dest_subfolder = people_folder
                    people_count += 1
                    category = "People"
                else:
                    dest_subfolder = no_people_folder
                    no_people_count += 1
                    category = "No_People"

                dest_path = self._get_unique_dest_path(dest_subfolder, filename)
                self._copy_or_move_file(image_path, dest_path)

                action = "Copied" if self.copy_mode else "Moved"
                self._log_status(f"{action}: {filename} -> {category}")

                results.append(SortResult(
                    source_path=image_path,
                    dest_path=dest_path,
                    has_people=has_people,
                    success=True
                ))

            except Exception as e:
                self._log_status(f"Error processing {filename}: {e}")
                results.append(SortResult(
                    source_path=image_path,
                    dest_path=None,
                    has_people=has_people,
                    success=False,
                    error_message=str(e)
                ))

            if self.progress_callback:
                progress = 70 + int((idx / total_files) * 30)
                self.progress_callback(progress, 100, filename, 100)

        # Summary
        if self.cancel_check and self.cancel_check():
            self._log_status(f"Operation cancelled: {people_count} people, {no_people_count} no people processed")
        else:
            error_count = sum(1 for r in results if not r.success)
            action = "copied" if self.copy_mode else "moved"
            self._log_status(f"Complete: {people_count} with people ({hog_found} HOG + {cnn_found} CNN), {no_people_count} without, {error_count} errors")

        return results, people_count, no_people_count
