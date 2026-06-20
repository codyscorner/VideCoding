"""Face detection module for Image People Sorter - Three-pass detection strategy

Pass 1a: HOG face scan upsample=1 (CPU parallel) - fast, catches large/clear faces
Pass 1b: HOG face scan upsample=2 (CPU parallel) - slower, catches smaller/partial faces
Pass 2:  YOLOv8n person detection (GPU) - catches any pose, orientation, lighting
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed, BrokenExecutor
import numpy as np
from PIL import Image, ImageOps
import face_recognition


# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}

# Number of parallel workers for HOG face pass (CPU-based, fast)
MAX_WORKERS_HOG = 14

# YOLOv8 confidence threshold for person detection (lower = more sensitive, more false positives)
YOLO_CONFIDENCE = 0.30

# YOLOv8 model — 'yolov8n.pt' is the fastest/smallest; auto-downloads ~6MB on first run
YOLO_MODEL = 'yolov8n.pt'


@dataclass
class SortResult:
    """Result of sorting a single image"""
    source_path: str
    dest_path: Optional[str]
    has_people: bool
    success: bool
    error_message: Optional[str] = None


# Standalone functions for multiprocessing (must be at module level)
def _pil_to_rgb_array(image_path: str, max_size: int = 1024) -> np.ndarray:
    """
    Load any image and return a (H, W, 3) uint8 C-contiguous numpy array.

    Uses img.tobytes() instead of np.array(img) to guarantee raw 3-byte-per-pixel
    RGB output regardless of PIL version or conda environment quirks.
    """
    img = Image.open(image_path)

    # Normalize unusual modes before any other operation
    if img.mode in ('I', 'F', 'I;16', 'I;16B'):
        # 16/32-bit: normalize range to 0-255 via numpy, then rebuild as L
        raw = np.array(img, dtype=np.float32)
        mx = raw.max()
        if mx > 0:
            raw = raw / mx * 255
        img = Image.fromarray(raw.astype(np.uint8), mode='L')
    elif img.mode == 'P':
        img = img.convert('RGBA')

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img = ImageOps.exif_transpose(img)

    # Ensure it's still RGB after transpose (defensive)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.BILINEAR)

    # Use tobytes() — always yields raw 3×uint8 per pixel for an RGB image,
    # no matter what numpy/PIL version is in the worker environment
    w, h = img.size
    arr = np.frombuffer(img.tobytes(), dtype=np.uint8).reshape(h, w, 3).copy()
    return arr


def _detect_faces_hog(image_path: str, upsample: int = 1) -> Tuple[str, bool, Optional[str]]:
    """
    Face detection using HOG model.
    upsample=1 is fast (catches large/clear faces).
    upsample=2 is slower but catches smaller/partially visible faces.
    Returns: (image_path, has_faces, error_message)
    """
    arr = None
    try:
        arr = _pil_to_rgb_array(image_path)
        face_locations = face_recognition.face_locations(arr, number_of_times_to_upsample=upsample, model="hog")
        return (image_path, len(face_locations) > 0, None)
    except Exception as e:
        detail = str(e)
        return (image_path, False, detail)


class ImagePeopleSorter:
    """Sorts images based on whether they contain people - three-pass detection strategy"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        copy_mode: bool = True,
        max_workers_hog: int = MAX_WORKERS_HOG,
        max_workers_body: int = 0  # unused, kept for API compat
    ):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check
        self.copy_mode = copy_mode
        self.max_workers_hog = max_workers_hog

    def _log_status(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)

    def _get_image_files(self, folder: str, recursive: bool) -> List[str]:
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

        return list(set(str(f) for f in files))

    def _copy_or_move_file(self, source: str, dest: str) -> None:
        import shutil
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if self.copy_mode:
            shutil.copy2(source, dest)
        else:
            shutil.move(source, dest)

    def _get_unique_dest_path(self, dest_folder: str, filename: str) -> str:
        dest_path = os.path.join(dest_folder, filename)
        if not os.path.exists(dest_path):
            return dest_path

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
        Sort images into People and No_People folders using two-pass detection.

        Pass 1: HOG face scan (fast, frontal faces)
        Pass 2: OpenCV body scan (slower, catches people from behind/side/distance)

        Returns:
            Tuple of (results list, people count, no people count)
        """
        if not os.path.exists(source_folder):
            raise ValueError(f"Source folder does not exist: {source_folder}")

        people_folder = os.path.join(dest_folder, "People")
        no_people_folder = os.path.join(dest_folder, "No_People")
        os.makedirs(people_folder, exist_ok=True)
        os.makedirs(no_people_folder, exist_ok=True)

        mode_str = "recursively" if recursive else "in root folder only"
        self._log_status(f"Scanning source folder {mode_str}...")
        image_files = self._get_image_files(source_folder, recursive)

        if not image_files:
            self._log_status("No image files found in source folder")
            return [], 0, 0

        total_files = len(image_files)
        self._log_status(f"Found {total_files} images to process")

        detection_results = {}
        needs_body_scan = []

        # =========================================
        # PASS 1a: HOG face scan — upsample=1 (fast, catches large/clear faces)
        # =========================================
        self._log_status(f"Pass 1a: Fast face scan with {self.max_workers_hog} workers...")
        processed = 0
        hog_found = 0
        error_count = 0
        needs_deep_face_scan = []  # images for Pass 1b (upsample=2)

        with ProcessPoolExecutor(max_workers=self.max_workers_hog) as executor:
            future_to_path = {executor.submit(_detect_faces_hog, path, 1): path for path in image_files}

            try:
                for future in as_completed(future_to_path):
                    if self.cancel_check and self.cancel_check():
                        executor.shutdown(wait=False, cancel_futures=True)
                        self._log_status("Operation cancelled during Pass 1a")
                        return [], 0, 0

                    try:
                        image_path, has_people, error = future.result()
                    except Exception as e:
                        image_path = future_to_path[future]
                        has_people, error = False, str(e)

                    processed += 1
                    filename = os.path.basename(image_path)

                    if error:
                        detection_results[image_path] = (False, error)
                        error_count += 1
                        if error_count <= 3:
                            self._log_status(f"Error ({filename}): {error}")
                        elif error_count == 4:
                            self._log_status("(further errors suppressed)")
                    elif has_people:
                        detection_results[image_path] = (True, None)
                        hog_found += 1
                        self._log_status(f"[Face] Found: {filename}")
                    else:
                        needs_deep_face_scan.append(image_path)

                    if self.progress_callback:
                        progress = int((processed / total_files) * 35)
                        self.progress_callback(progress, 100, f"Face scan: {filename}", 100)

            except BrokenExecutor:
                self._log_status("Operation cancelled during Pass 1a")
                return [], 0, 0

        self._log_status(
            f"Pass 1a complete: {hog_found} faces found, "
            f"{len(needs_deep_face_scan)} going to deep face scan"
        )

        # =========================================
        # PASS 1b: HOG face scan — upsample=2 (slower, catches smaller/partial faces)
        # Only runs on images Pass 1a missed — typically much smaller subset
        # =========================================
        hog_deep_found = 0
        if needs_deep_face_scan:
            deep_total = len(needs_deep_face_scan)
            self._log_status(f"Pass 1b: Deep face scan ({deep_total} images)...")
            deep_processed = 0

            with ProcessPoolExecutor(max_workers=self.max_workers_hog) as executor:
                future_to_path = {executor.submit(_detect_faces_hog, path, 2): path for path in needs_deep_face_scan}

                try:
                    for future in as_completed(future_to_path):
                        if self.cancel_check and self.cancel_check():
                            executor.shutdown(wait=False, cancel_futures=True)
                            self._log_status("Operation cancelled during Pass 1b")
                            return [], 0, 0

                        try:
                            image_path, has_people, error = future.result()
                        except Exception as e:
                            image_path = future_to_path[future]
                            has_people, error = False, str(e)

                        deep_processed += 1
                        filename = os.path.basename(image_path)

                        if error:
                            detection_results[image_path] = (False, error)
                        elif has_people:
                            detection_results[image_path] = (True, None)
                            hog_deep_found += 1
                            self._log_status(f"[Face+] Found: {filename}")
                        else:
                            needs_body_scan.append(image_path)

                        if self.progress_callback:
                            progress = 35 + int((deep_processed / deep_total) * 20)
                            self.progress_callback(progress, 100, f"Deep face scan: {filename}", 100)

                except BrokenExecutor:
                    self._log_status("Operation cancelled during Pass 1b")
                    return [], 0, 0

            self._log_status(
                f"Pass 1b complete: {hog_deep_found} additional faces found, "
                f"{len(needs_body_scan)} images need body scan"
            )

        # =========================================
        # PASS 2: YOLOv8 person detection (GPU)
        # Catches any pose, orientation, lighting — rotated photos, cyclists, dancers, etc.
        # Runs in this thread; GPU parallelises internally, no subprocess needed.
        # =========================================
        body_found = 0
        if needs_body_scan:
            body_total = len(needs_body_scan)
            try:
                import torch
                from ultralytics import YOLO
                import warnings
                warnings.filterwarnings('ignore', category=UserWarning)

                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self._log_status(f"Pass 2: YOLO body scan ({body_total} images, device={device})...")

                model = YOLO(YOLO_MODEL)

                for i, image_path in enumerate(needs_body_scan):
                    if self.cancel_check and self.cancel_check():
                        self._log_status("Operation cancelled during Pass 2")
                        return [], 0, 0

                    filename = os.path.basename(image_path)
                    try:
                        results = model(image_path, classes=[0], verbose=False, device=device)
                        confs = [float(c) for r in results for c in r.boxes.conf]
                        has_people = any(c >= YOLO_CONFIDENCE for c in confs)
                    except Exception as e:
                        detection_results[image_path] = (False, str(e))
                        if self.progress_callback:
                            progress = 55 + int(((i + 1) / body_total) * 30)
                            self.progress_callback(progress, 100, f"YOLO scan: {filename}", 100)
                        continue

                    if has_people:
                        detection_results[image_path] = (True, None)
                        body_found += 1
                        self._log_status(f"[YOLO] Found: {filename}")
                    else:
                        detection_results[image_path] = (False, None)

                    if self.progress_callback:
                        progress = 55 + int(((i + 1) / body_total) * 30)
                        self.progress_callback(progress, 100, f"YOLO scan: {filename}", 100)

            except ImportError:
                self._log_status("Warning: ultralytics not installed — body scan skipped. Run: pip install ultralytics")
                for path in needs_body_scan:
                    detection_results[path] = (False, None)

            self._log_status(f"Pass 2 complete: {body_found} additional people found by YOLO")

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

            if self.progress_callback:
                progress = 85 + int((idx / total_files) * 15)
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

        if self.cancel_check and self.cancel_check():
            self._log_status(f"Operation cancelled: {people_count} people, {no_people_count} no people processed")
        else:
            error_count = sum(1 for r in results if not r.success)
            action = "copied" if self.copy_mode else "moved"
            self._log_status(
                f"Complete: {people_count} with people "
                f"({hog_found} face-fast + {hog_deep_found} face-deep + {body_found} body), "
                f"{no_people_count} without, {error_count} errors"
            )

        return results, people_count, no_people_count
