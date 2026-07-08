"""File operation classes for File Copy Move Manager application"""

import os
import shutil
import time
import fnmatch
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, field

from folder_organization import FolderOrganizer, FolderStructure


def format_file_size(size_bytes: float) -> str:
    """Format a byte count in human-readable units (e.g. "1.23 MB")."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


@dataclass
class FileOperationResult:
    """Result of a file operation"""
    success: bool
    source_file: str
    destination_file: Optional[str] = None
    error_message: Optional[str] = None
    file_size: int = 0
    copy_time: float = 0.0
    checksum_verified: Optional[bool] = None


class FileValidator:
    """Validates file operations and inputs"""

    @staticmethod
    def validate_file_mask(file_mask: str) -> List[str]:
        """
        Validate and normalize file mask patterns

        Args:
            file_mask: File mask pattern(s) to validate (e.g., "*.jpg, *.png" or "oct*.*")

        Returns:
            List of normalized patterns

        Raises:
            ValueError: If file mask is empty
        """
        file_mask = file_mask.strip()
        if not file_mask:
            raise ValueError("File mask cannot be empty")

        # Split by comma and normalize each pattern
        patterns = []
        for pattern in file_mask.split(','):
            pattern = pattern.strip()
            if not pattern:
                continue
            # If pattern doesn't contain *, add *. prefix for extension matching
            if '*' not in pattern and '?' not in pattern:
                if not pattern.startswith('.'):
                    pattern = '.' + pattern
                pattern = '*' + pattern
            patterns.append(pattern)

        if not patterns:
            raise ValueError("File mask cannot be empty")

        return patterns

    @staticmethod
    def validate_folder_exists(folder_path: str) -> None:
        """
        Validate that a folder exists

        Args:
            folder_path: Path to validate

        Raises:
            ValueError: If folder doesn't exist
        """
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder does not exist: {folder_path}")


class FileScanner:
    """Scans directories for files matching criteria"""

    @staticmethod
    def _matches_any_pattern(filename: str, patterns: List[str]) -> bool:
        """
        Check if filename matches any of the given patterns

        Args:
            filename: Filename to check
            patterns: List of glob patterns

        Returns:
            True if filename matches any pattern
        """
        filename_lower = filename.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(filename_lower, pattern.lower()):
                return True
        return False

    @staticmethod
    def get_files_with_patterns(
        folder_path: str,
        patterns: List[str],
        recursive: bool = False,
        min_size_bytes: Optional[float] = None,
        max_size_bytes: Optional[float] = None,
        max_days_old: Optional[int] = None,
        sort_order: str = "largest",
    ) -> List[tuple[str, str, int]]:
        """
        Scan folder for matching files, apply filters, and return them ordered
        per `sort_order`: "largest" (default, best for parallel load-balancing),
        "smallest" (fast-climbing progress count), "oldest" (oldest modified
        date first), or "directory" (scan order, preserves read locality on
        mechanical drives).

        Returns list of (full_path, relative_path, size_bytes) tuples.
        """
        from datetime import datetime, timedelta

        files = []
        now = datetime.now()
        cutoff = (now - timedelta(days=max_days_old)).timestamp() if max_days_old is not None else None

        def _accept(full_path: str, filename: str):
            if not FileScanner._matches_any_pattern(filename, patterns):
                return False, 0, 0.0
            try:
                st = os.stat(full_path)
            except OSError:
                return False, 0, 0.0
            size = st.st_size
            if min_size_bytes is not None and size < min_size_bytes:
                return False, 0, 0.0
            if max_size_bytes is not None and size > max_size_bytes:
                return False, 0, 0.0
            if cutoff is not None and st.st_mtime < cutoff:
                return False, 0, 0.0
            return True, size, st.st_mtime

        # Internal rows carry modified time for the "oldest" sort; it is
        # stripped before returning so the public tuple shape stays 3-wide.
        rows = []  # (full_path, rel_path, size, mtime)
        if recursive:
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    ok, size, mtime = _accept(full_path, filename)
                    if ok:
                        rel_path = os.path.relpath(full_path, folder_path)
                        rows.append((full_path, rel_path, size, mtime))
        else:
            for filename in os.listdir(folder_path):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path):
                    ok, size, mtime = _accept(full_path, filename)
                    if ok:
                        rows.append((full_path, filename, size, mtime))

        if sort_order == "largest":
            rows.sort(key=lambda x: x[2], reverse=True)
        elif sort_order == "smallest":
            rows.sort(key=lambda x: x[2])
        elif sort_order == "oldest":
            rows.sort(key=lambda x: x[3])  # oldest modified date first
        # "directory" (or anything else): leave in natural scan order
        return [(fp, rel, size) for fp, rel, size, _mtime in rows]


class FileCopier:
    """Handles file copying operations"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        folder_structure: FolderStructure = FolderStructure.FLAT,
        number_duplicates: bool = True,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        counters_callback: Optional[Callable[[int, int, int], None]] = None,
        verify_checksum: bool = False,
        incremental: bool = False,
        move_mode: bool = False,
        workers: int = 1,
        transfer_callback: Optional[Callable[[str, str, int], None]] = None,
        fatal_error_callback: Optional[Callable[[str], None]] = None,
        sort_order: str = "largest",
    ):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check
        self.counters_callback = counters_callback
        self.transfer_callback = transfer_callback
        self.fatal_error_callback = fatal_error_callback
        self.validator = FileValidator()
        self.scanner = FileScanner()
        self.folder_structure = folder_structure
        self.number_duplicates = number_duplicates
        self.organizer = FolderOrganizer()
        self.verify_checksum = verify_checksum
        self.incremental = incremental
        self.move_mode = move_mode
        self.workers = max(1, workers)
        self.sort_order = sort_order
        self._filename_lock = threading.Lock()
        self.last_activity_time: float = time.time()

    def _log_status(self, message: str) -> None:
        """Log status message if callback is set"""
        if self.status_callback:
            self.status_callback(message)

    def _compute_checksum(self, path: str) -> str:
        """Compute MD5 checksum of a file in 4 MB chunks."""
        h = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(4 * 1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def _truncate_path(self, folder: str, filename: str, max_len: int = 245) -> str:
        """
        If the full path exceeds max_len, truncate the filename stem and append _tr001.
        Returns the (possibly truncated) filename only.
        """
        full_path = os.path.join(folder, filename)
        if len(full_path) <= max_len:
            return filename
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while True:
            suffix = f"_tr_{counter:03d}"
            allowed = max_len - len(folder) - len(os.sep) - len(suffix) - len(ext)
            truncated = f"{base_name[:allowed]}{suffix}{ext}"
            if not os.path.exists(os.path.join(folder, truncated)):
                break
            counter += 1
        self._log_status(f"Path too long, truncated: {filename} → {truncated}")
        return truncated

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format (e.g. "1.23 MB")."""
        return format_file_size(size_bytes)

    def copy_files(
        self,
        source_folder: str,
        dest_folder: str,
        file_mask: str,
        preserve_structure: bool = False,
        recursive: bool = True,
        min_size_bytes: Optional[float] = None,
        max_size_bytes: Optional[float] = None,
        max_days_old: Optional[int] = None,
        pre_scanned_files: Optional[List[tuple]] = None,
    ) -> List[FileOperationResult]:
        """
        Copy files from source to destination

        Args:
            source_folder: Source folder path
            dest_folder: Destination folder path
            file_mask: File mask pattern(s) to match (e.g., "*.jpg, *.png" or "oct*.*")
            preserve_structure: If True, preserve original folder structure
            recursive: If True, search subfolders recursively
            min_size_bytes: Minimum file size in bytes (inclusive)
            max_size_bytes: Maximum file size in bytes (inclusive)
            max_days_old: Maximum file age in days

        Returns:
            List of FileOperationResult objects

        Raises:
            ValueError: If validation fails
            OSError: If folders cannot be accessed
        """
        # Validate inputs
        self.validator.validate_folder_exists(source_folder)
        patterns = self.validator.validate_file_mask(file_mask)

        # Create destination folder if it doesn't exist
        self._log_status(f"Checking destination folder...")
        os.makedirs(dest_folder, exist_ok=True)

        # Determine if we should use preserve mode
        structure = FolderStructure.PRESERVE if preserve_structure else self.folder_structure

        if pre_scanned_files is not None:
            # File list already determined by preview — skip re-scan
            filtered_files = pre_scanned_files
            self._log_status(f"Using {len(filtered_files)} file(s) from preview scan...")
            if not filtered_files:
                self._log_status("No files to copy (all up-to-date per preview scan)")
                return []
        else:
            # Scan, filter, and sort in one pass (smallest first)
            search_mode = "recursively through all subfolders" if recursive else "in root folder only"
            patterns_str = ", ".join(patterns)
            self._log_status(f"Reading directories {search_mode}...")
            self._log_status(f"Gathering file list — matching: {patterns_str}")
            filtered_files = self.scanner.get_files_with_patterns(
                source_folder, patterns, recursive,
                min_size_bytes=min_size_bytes,
                max_size_bytes=max_size_bytes,
                max_days_old=max_days_old,
                sort_order=self.sort_order,
            )

            if not filtered_files:
                self._log_status(f"No files found matching '{patterns_str}'")
                return []

            _order_desc = {
                "largest": "largest to smallest",
                "smallest": "smallest to largest",
                "oldest": "oldest modified date first",
                "directory": "directory order",
            }.get(self.sort_order, "largest to smallest")
            self._log_status(f"Found {len(filtered_files)} files — ordering {_order_desc}...")

        op_verb = "move" if self.move_mode else "copy"
        worker_str = f" ({self.workers} workers)" if self.workers > 1 else ""
        self._log_status(f"Starting {op_verb} operations{worker_str}...")

        total = len(filtered_files)
        results = []

        if self.workers <= 1:
            # ── Sequential path ──────────────────────────────────────────────
            for idx, (full_path, rel_path, file_size) in enumerate(filtered_files, 1):
                if self.cancel_check and self.cancel_check():
                    self._log_status("Operation cancelled by user")
                    break

                filename = os.path.basename(full_path)
                show_file_progress = file_size >= 50 * 1024 * 1024

                if self.progress_callback:
                    self.progress_callback(idx, total, filename, 0 if show_file_progress else -1)

                result = self._process_single_file(
                    full_path, rel_path, source_folder, dest_folder, structure, idx, total
                )
                results.append(result)

                if self.progress_callback:
                    self.progress_callback(idx, total, filename, 100 if show_file_progress else -1)

                if self.counters_callback:
                    copied_n  = sum(1 for r in results if r.success and r.destination_file is not None)
                    skipped_n = sum(1 for r in results if r.success and r.destination_file is None)
                    errors_n  = sum(1 for r in results if not r.success)
                    self.counters_callback(copied_n, skipped_n, errors_n)

        else:
            # ── Parallel path ─────────────────────────────────────────────────
            _lock = threading.Lock()
            _counts = [0, 0, 0, 0]  # [completed, copied, skipped, errors]

            def _worker(item):
                full_path, rel_path, _ = item
                if self.cancel_check and self.cancel_check():
                    return FileOperationResult(
                        success=True, source_file=os.path.basename(full_path),
                        destination_file=None, error_message="Cancelled"
                    )
                result = self._process_single_file(
                    full_path, rel_path, source_folder, dest_folder, structure, 0, 0
                )
                fname = os.path.basename(full_path)
                with _lock:
                    _counts[0] += 1
                    self.last_activity_time = time.time()
                    if result.success and result.destination_file is not None:
                        _counts[1] += 1
                    elif result.success:
                        _counts[2] += 1
                    else:
                        _counts[3] += 1
                    if self.progress_callback:
                        self.progress_callback(_counts[0], total, fname, -1)
                    if self.counters_callback:
                        self.counters_callback(_counts[1], _counts[2], _counts[3])
                return result

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {executor.submit(_worker, item): item for item in filtered_files}
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        fname = os.path.basename(futures[future][0])
                        self._log_status(f"Error: {fname} — {e}")
                        results.append(FileOperationResult(
                            success=False, source_file=fname, error_message=str(e)
                        ))


        # Summary
        op_verb_past = "moved" if self.move_mode else "copied"
        if self.cancel_check and self.cancel_check():
            copied_count = sum(1 for r in results if r.success and r.destination_file is not None)
            self._log_status(f"Operation cancelled: {copied_count} files {op_verb_past} before cancellation")
        else:
            copied_count = sum(1 for r in results if r.success and r.destination_file is not None)
            skipped_count = sum(1 for r in results if r.success and r.destination_file is None)
            error_count = sum(1 for r in results if not r.success)
            total_bytes = sum(r.file_size for r in results if r.success and r.destination_file is not None)
            self._log_status(
                f"Operation completed: {copied_count} {op_verb_past} ({format_file_size(total_bytes)}), "
                f"{skipped_count} skipped, {error_count} errors"
            )

        return results

    def _process_single_file(
        self,
        source_path: str,
        rel_path: str,
        source_root: str,
        dest_folder: str,
        structure: FolderStructure,
        idx: int = 0,
        total: int = 0
    ) -> FileOperationResult:
        """
        Process a single file

        Args:
            source_path: Full path to source file
            rel_path: Relative path from source root
            source_root: Root source folder
            dest_folder: Destination folder path
            structure: Folder organization structure

        Returns:
            FileOperationResult object
        """
        filename = os.path.basename(source_path)

        # Determine destination folder with organization
        if structure == FolderStructure.PRESERVE:
            # Preserve original folder structure
            rel_dir = os.path.dirname(rel_path)
            if rel_dir:
                final_dest_folder = self.organizer.create_folder_structure(dest_folder, rel_dir)
            else:
                final_dest_folder = dest_folder
        else:
            # Use specified folder organization
            subfolder = self.organizer.get_destination_subfolder(
                source_path,
                structure,
                source_root,
                use_file_date=True
            )
            if subfolder:
                final_dest_folder = self.organizer.create_folder_structure(dest_folder, subfolder)
            else:
                final_dest_folder = dest_folder

        LARGE_FILE_THRESHOLD = 120 * 1024 * 1024  # 120 MB — use chunked I/O above this
        MIN_FILE_PROGRESS_SIZE = 50 * 1024 * 1024  # 50 MB — skip per-file bar below this
        CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
        MAX_RETRIES = 3
        RETRY_DELAY = 1.5

        dest_path = ""
        try:
            # ── Thread-safe filename resolution + reservation ─────────────────
            # Lock ensures two parallel workers can't claim the same dest path.
            with self._filename_lock:
                final_filename = self._truncate_path(final_dest_folder, filename)
                dest_path = os.path.join(final_dest_folder, final_filename)
                skip_result = None

                if os.path.exists(dest_path):
                    if self.incremental:
                        try:
                            src_stat = os.stat(source_path)
                            dst_stat = os.stat(dest_path)
                            if (src_stat.st_size == dst_stat.st_size and
                                    abs(src_stat.st_mtime - dst_stat.st_mtime) <= 2.0):
                                self._log_status(f"Skipped (unchanged): {filename}")
                                skip_result = FileOperationResult(
                                    success=True, source_file=filename,
                                    destination_file=None, error_message="Skipped (unchanged)"
                                )
                            # else: file changed — fall through and overwrite it
                        except OSError:
                            pass

                    if skip_result is None and not self.incremental:
                        # Non-incremental mode: handle duplicates per user setting
                        if self.number_duplicates:
                            # Before renaming, verify whether the collision is a true
                            # duplicate (identical content) or just a name/size coincidence.
                            # Only hash when sizes match — different sizes skip straight to
                            # rename with zero I/O overhead.
                            try:
                                if os.path.getsize(source_path) == os.path.getsize(dest_path):
                                    src_hash = self._compute_checksum(source_path)
                                    self.last_activity_time = time.time()
                                    dst_hash = self._compute_checksum(dest_path)
                                    self.last_activity_time = time.time()
                                    if src_hash == dst_hash:
                                        self._log_status(f"Skipped (identical): {filename}")
                                        skip_result = FileOperationResult(
                                            success=True, source_file=filename,
                                            destination_file=None,
                                            error_message="Skipped (identical)"
                                        )
                            except OSError:
                                pass

                            if skip_result is None:
                                base_name, ext = os.path.splitext(filename)
                                counter = 1
                                while os.path.exists(dest_path):
                                    final_filename = f"{base_name}_{counter:03d}{ext}"
                                    dest_path = os.path.join(final_dest_folder, final_filename)
                                    counter += 1
                                self._log_status(f"Duplicate found: {filename} → {final_filename}")
                        else:
                            self._log_status(f"Skipped (duplicate): {filename}")
                            skip_result = FileOperationResult(
                                success=True, source_file=filename,
                                destination_file=None, error_message="Skipped (duplicate)"
                            )

                if skip_result is None:
                    # Reserve the path so other workers pick a different name
                    try:
                        open(dest_path, 'wb').close()
                    except OSError:
                        pass

            if skip_result is not None:
                return skip_result

            # Get file size
            file_size = os.path.getsize(source_path)
            self.last_activity_time = time.time()

            _show_transfer = (self.transfer_callback is not None and file_size >= MIN_FILE_PROGRESS_SIZE)
            if _show_transfer:
                self.transfer_callback(source_path, filename, 0)

            # Copy with retry loop (handles transient network errors)
            start_time = time.time()
            for attempt in range(MAX_RETRIES):
                try:
                    if file_size >= LARGE_FILE_THRESHOLD:
                        # Always chunk large files so last_activity_time stays current
                        copied_bytes = 0
                        with open(source_path, 'rb') as src, open(dest_path, 'wb') as dst:
                            while True:
                                if self.cancel_check and self.cancel_check():
                                    break
                                chunk = src.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                dst.write(chunk)
                                copied_bytes += len(chunk)
                                self.last_activity_time = time.time()
                                pct = int(copied_bytes / file_size * 100)
                                if self.progress_callback and total > 0:
                                    self.progress_callback(idx, total, filename, pct)
                                if _show_transfer:
                                    self.transfer_callback(source_path, filename, pct)
                        shutil.copystat(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
                    break  # copy succeeded
                except OSError as copy_err:
                    if self.cancel_check and self.cancel_check():
                        break
                    # Detect unrecoverable errors — retrying more files would be pointless
                    _winerr = getattr(copy_err, 'winerror', None)
                    _FATAL_WINERRORS = {
                        112,   # ERROR_DISK_FULL
                        39,    # ERROR_DISK_FULL (alt)
                        21,    # ERROR_NOT_READY (drive disconnected)
                        1117,  # ERROR_IO_DEVICE
                        1392,  # ERROR_FILE_CORRUPT
                    }
                    _is_fatal = copy_err.errno == 28 or _winerr in _FATAL_WINERRORS
                    if _is_fatal:
                        _reason = (
                            "Destination disk is full" if (_winerr in (112, 39) or copy_err.errno == 28)
                            else "Destination drive is not ready or disconnected" if _winerr in (21, 1117)
                            else "Destination disk or file is corrupt"
                        )
                        fatal_msg = f"{_reason}: {copy_err}"
                        self._log_status(f"FATAL: {fatal_msg}")
                        if self.fatal_error_callback:
                            self.fatal_error_callback(fatal_msg)
                        raise OSError(fatal_msg) from copy_err
                    # If destination is read-only, strip the flag and retry immediately
                    err_str = str(copy_err)
                    if copy_err.errno == 13 and dest_path in err_str:
                        try:
                            import stat as _stat
                            os.chmod(dest_path, _stat.S_IWRITE | _stat.S_IREAD)
                            continue  # retry without counting this as an attempt
                        except OSError:
                            pass
                    side = "reading source" if source_path in err_str else "writing destination" if dest_path in err_str else "during copy"
                    if attempt < MAX_RETRIES - 1:
                        self._log_status(f"Retry {attempt + 1}/{MAX_RETRIES - 1}: {filename} ({side}) — {copy_err}")
                        time.sleep(RETRY_DELAY)
                    else:
                        raise OSError(f"[{side}] {copy_err}") from copy_err
            copy_time = time.time() - start_time
            if _show_transfer:
                self.transfer_callback(source_path, filename, -1)

            # Checksum verification
            checksum_ok: Optional[bool] = None
            if self.verify_checksum and not (self.cancel_check and self.cancel_check()):
                src_hash = self._compute_checksum(source_path)
                dst_hash = self._compute_checksum(dest_path)
                checksum_ok = (src_hash == dst_hash)
                if not checksum_ok:
                    self._log_status(f"CHECKSUM FAILED: {filename}")
                    return FileOperationResult(
                        success=False,
                        source_file=filename,
                        destination_file=final_filename,
                        error_message="Checksum mismatch — file may be corrupted",
                        file_size=file_size,
                        copy_time=copy_time,
                        checksum_verified=False
                    )

            # Move mode: delete source after successful copy+verify
            if self.move_mode:
                try:
                    os.remove(source_path)
                except OSError as del_err:
                    self._log_status(f"Warning: source not deleted after move: {filename} — {del_err}")

            # Only log large files individually; small files are counted silently
            verb = "Moved" if self.move_mode else "Copied"
            if file_size >= LARGE_FILE_THRESHOLD:
                size_str = self._format_file_size(file_size)
                time_str = f"{copy_time:.2f}s"
                verified_tag = " ✓" if checksum_ok else ""
                self._log_status(f"{verb} (large): {filename} ({size_str}, {time_str}){verified_tag}")

            return FileOperationResult(
                success=True,
                source_file=filename,
                destination_file=final_filename,
                file_size=file_size,
                copy_time=copy_time,
                checksum_verified=checksum_ok
            )
        except Exception as e:
            err_str = str(e)
            if source_path in err_str:
                side = "reading source"
            elif dest_path and dest_path in err_str:
                side = "writing destination"
            else:
                side = "copying"
            self._log_status(f"Error {side} — {filename}: {e}")
            return FileOperationResult(
                success=False,
                source_file=filename,
                error_message=str(e)
            )
