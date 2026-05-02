"""File hashing and deduplication module for File Hash Dedupe"""

import os
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# Number of parallel workers for hashing (I/O bound, can use many)
MAX_WORKERS = 16

# Buffer size for reading files (64KB chunks)
BUFFER_SIZE = 65536


@dataclass
class DedupeResult:
    """Result of deduplication operation"""
    source_path: str
    dest_path: Optional[str]
    file_hash: str
    is_duplicate: bool
    is_primary: bool
    moved: bool
    error_message: Optional[str] = None


def _compute_file_hash(file_path: str) -> Tuple[str, str, Optional[str]]:
    """
    Compute MD5 hash of a file

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (file_path, hash_hex, error_message)
    """
    try:
        hasher = hashlib.md5()

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                hasher.update(data)

        return (file_path, hasher.hexdigest(), None)

    except Exception as e:
        return (file_path, '', str(e))


class FileDeduplicator:
    """Finds and moves duplicate files based on hash comparison"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        max_workers: int = MAX_WORKERS
    ):
        """
        Initialize the deduplicator

        Args:
            status_callback: Callback for status messages
            progress_callback: Callback for progress (current, total, filename)
            cancel_check: Callback that returns True if operation should be cancelled
            max_workers: Number of parallel workers for hashing
        """
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check
        self.max_workers = max_workers

    def _log_status(self, message: str) -> None:
        """Log a status message"""
        if self.status_callback:
            self.status_callback(message)

    def _get_all_files(self, folder: str, recursive: bool) -> List[str]:
        """
        Get all files in a folder

        Args:
            folder: Folder to scan
            recursive: If True, scan subdirectories

        Returns:
            List of file paths
        """
        files = []
        folder_path = Path(folder)

        if recursive:
            for item in folder_path.rglob('*'):
                if item.is_file():
                    # Skip files in Dupes folder
                    if 'Dupes' not in item.parts:
                        files.append(str(item))
        else:
            for item in folder_path.glob('*'):
                if item.is_file():
                    files.append(str(item))

        return files

    def find_and_move_duplicates(
        self,
        source_folder: str,
        recursive: bool = True,
        permanent_delete: bool = False
    ) -> Tuple[List[DedupeResult], int, int, int]:
        """
        Find duplicate files and move them to Dupes subfolder

        Strategy:
        1. Hash all files in parallel
        2. Group files by hash
        3. For each hash with multiple files, keep first as primary
        4. Move all other files with same hash to Dupes folder

        Args:
            source_folder: Folder to scan for duplicates
            recursive: If True, scan subdirectories

        Returns:
            Tuple of (results list, total files, unique files, duplicates moved)
        """
        # Validate folder
        if not os.path.exists(source_folder):
            raise ValueError(f"Source folder does not exist: {source_folder}")

        # Create Dupes folder (only needed when not permanently deleting)
        dupes_folder = os.path.join(source_folder, "Dupes")
        if not permanent_delete:
            os.makedirs(dupes_folder, exist_ok=True)

        # Get all files
        mode_str = "recursively" if recursive else "in root folder only"
        self._log_status(f"Scanning source folder {mode_str}...")
        all_files = self._get_all_files(source_folder, recursive)

        if not all_files:
            self._log_status("No files found in source folder")
            return [], 0, 0, 0

        total_files = len(all_files)
        self._log_status(f"Found {total_files} files to hash")

        # =========================================
        # PASS 1: Hash all files in parallel
        # =========================================
        self._log_status(f"Pass 1: Hashing files with {self.max_workers} workers...")

        file_hashes: Dict[str, str] = {}  # file_path -> hash
        hash_errors: Dict[str, str] = {}  # file_path -> error
        processed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(_compute_file_hash, path): path
                for path in all_files
            }

            for future in as_completed(future_to_path):
                if self.cancel_check and self.cancel_check():
                    self._log_status("Cancellation requested...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    file_path, file_hash, error = future.result()
                    processed += 1
                    filename = os.path.basename(file_path)

                    if error:
                        hash_errors[file_path] = error
                        self._log_status(f"Error: {filename} - {error}")
                    else:
                        file_hashes[file_path] = file_hash

                    # Progress: Hashing is 70% of work
                    if self.progress_callback:
                        progress = int((processed / total_files) * 70)
                        self.progress_callback(progress, 100, f"Hashing: {filename}")

                except Exception as e:
                    path = future_to_path[future]
                    hash_errors[path] = str(e)
                    processed += 1

        if self.cancel_check and self.cancel_check():
            self._log_status("Operation cancelled during hashing")
            return [], 0, 0, 0

        self._log_status(f"Pass 1 complete: {len(file_hashes)} files hashed, {len(hash_errors)} errors")

        # =========================================
        # PASS 2: Group by hash and identify duplicates
        # =========================================
        self._log_status("Pass 2: Identifying duplicates...")

        # Group files by hash
        hash_to_files: Dict[str, List[str]] = defaultdict(list)
        for file_path, file_hash in file_hashes.items():
            hash_to_files[file_hash].append(file_path)

        # Identify primary files (first occurrence) and duplicates
        primary_files: Dict[str, str] = {}  # hash -> primary file path
        duplicate_files: List[Tuple[str, str]] = []  # (file_path, hash)

        for file_hash, files in hash_to_files.items():
            # Sort files to ensure consistent primary selection
            sorted_files = sorted(files)
            primary_files[file_hash] = sorted_files[0]

            # All others are duplicates
            for dup_file in sorted_files[1:]:
                duplicate_files.append((dup_file, file_hash))

        unique_count = len(primary_files)
        duplicate_count = len(duplicate_files)

        self._log_status(f"Found {unique_count} unique files, {duplicate_count} duplicates")

        # =========================================
        # PASS 3: Move or delete duplicates
        # =========================================
        action = "Deleting" if permanent_delete else "Moving"
        dest_desc = "permanently" if permanent_delete else "to Dupes folder"
        self._log_status(f"Pass 3: {action} {duplicate_count} duplicates {dest_desc}...")

        results = []
        moved_count = 0

        for file_hash, file_path in primary_files.items():
            results.append(DedupeResult(
                source_path=file_path,
                dest_path=None,
                file_hash=file_hash,
                is_duplicate=False,
                is_primary=True,
                moved=False
            ))

        for file_path, error in hash_errors.items():
            results.append(DedupeResult(
                source_path=file_path,
                dest_path=None,
                file_hash='',
                is_duplicate=False,
                is_primary=False,
                moved=False,
                error_message=error
            ))

        for idx, (file_path, file_hash) in enumerate(duplicate_files, 1):
            if self.cancel_check and self.cancel_check():
                self._log_status("Operation cancelled by user")
                break

            filename = os.path.basename(file_path)

            if self.progress_callback:
                progress = 70 + int((idx / max(duplicate_count, 1)) * 30)
                self.progress_callback(progress, 100, f"{action}: {filename}")

            try:
                primary_name = os.path.basename(primary_files[file_hash])

                if permanent_delete:
                    os.unlink(file_path)
                    moved_count += 1
                    if idx % 100 == 0 or idx == duplicate_count:
                        self._log_status(f"Deleted {moved_count} of {duplicate_count} duplicates...")
                    results.append(DedupeResult(
                        source_path=file_path,
                        dest_path=None,
                        file_hash=file_hash,
                        is_duplicate=True,
                        is_primary=False,
                        moved=True
                    ))
                else:
                    dest_path = self._get_unique_dest_path(dupes_folder, filename)
                    shutil.move(file_path, dest_path)
                    moved_count += 1
                    self._log_status(f"Moved: {filename} (dup of {primary_name})")
                    results.append(DedupeResult(
                        source_path=file_path,
                        dest_path=dest_path,
                        file_hash=file_hash,
                        is_duplicate=True,
                        is_primary=False,
                        moved=True
                    ))

            except Exception as e:
                self._log_status(f"Error {action.lower()} {filename}: {e}")
                results.append(DedupeResult(
                    source_path=file_path,
                    dest_path=None,
                    file_hash=file_hash,
                    is_duplicate=True,
                    is_primary=False,
                    moved=False,
                    error_message=str(e)
                ))

        # Summary
        action_past = "deleted" if permanent_delete else "moved"
        if self.cancel_check and self.cancel_check():
            self._log_status(f"Operation cancelled: {moved_count} duplicates {action_past}")
        else:
            error_count = len(hash_errors) + sum(1 for r in results if r.is_duplicate and not r.moved)
            self._log_status(f"Complete: {unique_count} unique, {moved_count} duplicates {action_past}, {error_count} errors")

        return results, total_files, unique_count, moved_count

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
