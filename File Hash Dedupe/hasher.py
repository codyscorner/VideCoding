"""File hashing and deduplication module for File Hash Dedupe"""

import os
import csv
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

# Hash algorithms offered in the UI (both are stdlib — no extra dependency)
ALGORITHMS = {"MD5": "md5", "BLAKE2b": "blake2b"}

# Rules for picking which copy of a duplicate group survives as primary
KEEP_RULES = ["First (alphabetical)", "Oldest", "Newest", "Shortest path"]


@dataclass
class FileEntry:
    """A file discovered during a scan, with metadata filled in progressively"""
    path: str
    size: int
    mtime: float
    file_hash: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DedupeResult:
    """Result of a single file's dedupe operation"""
    source_path: str
    dest_path: Optional[str]
    file_hash: str
    is_duplicate: bool
    is_primary: bool
    moved: bool
    error_message: Optional[str] = None


@dataclass
class ScanResult:
    """Result of a scan pass: duplicate groups found, ready for preview or execution"""
    groups: Dict[str, List[FileEntry]]   # hash -> entries (len >= 2)
    primary_map: Dict[str, FileEntry]    # hash -> chosen primary entry (kept, never moved)
    hash_errors: Dict[str, str]          # path -> error message
    total_files: int
    unique_count: int
    keep_rule: str


def _compute_file_hash(file_path: str, algorithm: str = "md5") -> Tuple[str, str, Optional[str]]:
    """Compute a hash of a file's contents"""
    try:
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                hasher.update(data)
        return (file_path, hasher.hexdigest(), None)
    except Exception as e:
        return (file_path, '', str(e))


def _keep_rule_sort_key(entry: FileEntry, keep_rule: str):
    if keep_rule == "Oldest":
        return (entry.mtime, entry.path)
    if keep_rule == "Newest":
        return (-entry.mtime, entry.path)
    if keep_rule == "Shortest path":
        return (len(entry.path), entry.path)
    return (entry.path,)  # First (alphabetical)


def choose_primary(entries: List[FileEntry], keep_rule: str) -> FileEntry:
    """Pick which file in a duplicate group survives, per the given keep rule"""
    return sorted(entries, key=lambda e: _keep_rule_sort_key(e, keep_rule))[0]


def write_csv_report(csv_path: str, groups: Dict[str, List[FileEntry]], primary_map: Dict[str, FileEntry],
                      results: Optional[List[DedupeResult]] = None) -> None:
    """Write a CSV report of duplicate groups, and the action taken per file if results are given"""
    action_by_path = {}
    if results:
        for r in results:
            if r.is_primary:
                action_by_path[r.source_path] = "kept"
            elif r.error_message:
                action_by_path[r.source_path] = f"error: {r.error_message}"
            elif r.moved and r.dest_path:
                action_by_path[r.source_path] = f"moved to {r.dest_path}"
            elif r.moved:
                action_by_path[r.source_path] = "deleted"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["group_hash", "role", "path", "size_bytes", "action"])
        for file_hash, entries in groups.items():
            primary = primary_map[file_hash]
            for entry in sorted(entries, key=lambda e: e.path):
                role = "primary" if entry.path == primary.path else "duplicate"
                default_action = "kept" if role == "primary" else "pending"
                action = action_by_path.get(entry.path, default_action)
                writer.writerow([file_hash, role, entry.path, entry.size, action])


class FileDeduplicator:
    """Finds and moves duplicate files based on hash comparison"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        max_workers: int = MAX_WORKERS
    ):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check
        self.max_workers = max_workers

    def _log_status(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)

    def _report_progress(self, current: int, total: int, filename: str) -> None:
        if self.progress_callback:
            self.progress_callback(current, total, filename)

    def _get_all_files(self, folder: str, recursive: bool) -> List[str]:
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

    def _stat_entries(self, paths: List[str]) -> List[FileEntry]:
        entries = []
        for p in paths:
            try:
                st = os.stat(p)
                entries.append(FileEntry(path=p, size=st.st_size, mtime=st.st_mtime))
            except OSError as e:
                entries.append(FileEntry(path=p, size=-1, mtime=0.0, error=str(e)))
        return entries

    def _hash_entries(self, entries: List[FileEntry], algorithm: str,
                       progress_start: int, progress_end: int) -> Dict[str, str]:
        """Hash entries in parallel (fills in entry.file_hash), reporting progress within the given range"""
        to_hash = [e for e in entries if e.error is None]
        total = len(to_hash)
        errors: Dict[str, str] = {}
        if total == 0:
            return errors

        by_path = {e.path: e for e in to_hash}
        processed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_compute_file_hash, e.path, algorithm): e.path for e in to_hash}

            for future in as_completed(futures):
                if self.cancel_check and self.cancel_check():
                    self._log_status("Cancellation requested...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                path = futures[future]
                try:
                    _, file_hash, error = future.result()
                except Exception as e:
                    file_hash, error = '', str(e)

                processed += 1
                filename = os.path.basename(path)

                if error:
                    errors[path] = error
                    by_path[path].error = error
                    self._log_status(f"Error: {filename} - {error}")
                else:
                    by_path[path].file_hash = file_hash

                progress = progress_start + int((processed / total) * (progress_end - progress_start))
                self._report_progress(progress, 100, f"Hashing: {filename}")

        return errors

    # ---------- Single-folder dedupe ----------

    def scan(self, source_folder: str, recursive: bool = True, algorithm: str = "md5",
             keep_rule: str = "First (alphabetical)",
             progress_start: int = 0, progress_end: int = 70) -> ScanResult:
        """
        Scan a folder for duplicates without touching any files.

        Strategy:
        1. Stat all files (size + mtime), cheap
        2. Size pre-filter: only files that share a size with another file can possibly be duplicates
        3. Hash the candidates in parallel
        4. Group by hash, pick a primary per group using the keep rule
        """
        if not os.path.exists(source_folder):
            raise ValueError(f"Source folder does not exist: {source_folder}")

        mode_str = "recursively" if recursive else "in root folder only"
        self._log_status(f"Scanning source folder {mode_str}...")
        all_paths = self._get_all_files(source_folder, recursive)

        if not all_paths:
            self._log_status("No files found in source folder")
            return ScanResult({}, {}, {}, 0, 0, keep_rule)

        total_files = len(all_paths)
        self._log_status(f"Found {total_files} files")
        entries = self._stat_entries(all_paths)

        by_size: Dict[int, List[FileEntry]] = defaultdict(list)
        for e in entries:
            if e.error is None:
                by_size[e.size].append(e)

        candidates = [e for group in by_size.values() if len(group) > 1 for e in group]
        skipped_unique = sum(1 for group in by_size.values() if len(group) == 1)
        self._log_status(
            f"Size pre-filter: {len(candidates)} file(s) share a size with another file "
            f"({skipped_unique} unique-size file(s) skipped, no hashing needed)"
        )

        if self.cancel_check and self.cancel_check():
            return ScanResult({}, {}, {}, 0, 0, keep_rule)

        self._log_status(f"Hashing {len(candidates)} file(s) with {self.max_workers} workers ({algorithm.upper()})...")
        hash_errors = self._hash_entries(candidates, algorithm, progress_start, progress_end)

        if self.cancel_check and self.cancel_check():
            self._log_status("Operation cancelled during hashing")
            return ScanResult({}, {}, {}, 0, 0, keep_rule)

        by_hash: Dict[str, List[FileEntry]] = defaultdict(list)
        for e in candidates:
            if e.file_hash is not None:
                by_hash[e.file_hash].append(e)

        groups = {h: es for h, es in by_hash.items() if len(es) > 1}
        primary_map = {h: choose_primary(es, keep_rule) for h, es in groups.items()}

        duplicate_count = sum(len(es) - 1 for es in groups.values())
        unique_count = total_files - duplicate_count - len(hash_errors)

        self._log_status(f"Found {len(groups)} duplicate group(s), {duplicate_count} duplicate file(s)")

        return ScanResult(groups, primary_map, hash_errors, total_files, unique_count, keep_rule)

    def rescan_keep_rule(self, scan_result: ScanResult, keep_rule: str) -> ScanResult:
        """Recompute which file survives per group under a new keep rule, without re-hashing"""
        primary_map = {h: choose_primary(es, keep_rule) for h, es in scan_result.groups.items()}
        return ScanResult(scan_result.groups, primary_map, scan_result.hash_errors,
                           scan_result.total_files, scan_result.unique_count, keep_rule)

    def execute(self, scan_result: ScanResult, source_folder: str, permanent_delete: bool = False,
                progress_start: int = 70, progress_end: int = 100) -> Tuple[List[DedupeResult], int, int, int]:
        """Move (or delete) every non-primary file in each duplicate group"""
        dupes_folder = os.path.join(source_folder, "Dupes")
        if not permanent_delete:
            os.makedirs(dupes_folder, exist_ok=True)

        results: List[DedupeResult] = []
        for file_hash, primary in scan_result.primary_map.items():
            results.append(DedupeResult(primary.path, None, file_hash, False, True, False))
        for path, error in scan_result.hash_errors.items():
            results.append(DedupeResult(path, None, '', False, False, False, error_message=error))

        duplicates: List[Tuple[str, FileEntry]] = []
        for file_hash, entries in scan_result.groups.items():
            primary = scan_result.primary_map[file_hash]
            for e in entries:
                if e.path != primary.path:
                    duplicates.append((file_hash, e))

        duplicate_count = len(duplicates)
        action = "Deleting" if permanent_delete else "Moving"
        dest_desc = "permanently" if permanent_delete else "to Dupes folder"
        self._log_status(f"{action} {duplicate_count} duplicate(s) {dest_desc}...")

        moved_count = 0
        for idx, (file_hash, entry) in enumerate(duplicates, 1):
            if self.cancel_check and self.cancel_check():
                self._log_status("Operation cancelled by user")
                break

            filename = os.path.basename(entry.path)
            progress = progress_start + int((idx / max(duplicate_count, 1)) * (progress_end - progress_start))
            self._report_progress(progress, 100, f"{action}: {filename}")

            primary_name = os.path.basename(scan_result.primary_map[file_hash].path)
            try:
                if permanent_delete:
                    os.unlink(entry.path)
                    moved_count += 1
                    results.append(DedupeResult(entry.path, None, file_hash, True, False, True))
                else:
                    dest_path = self._get_unique_dest_path(dupes_folder, filename)
                    shutil.move(entry.path, dest_path)
                    moved_count += 1
                    self._log_status(f"Moved: {filename} (dup of {primary_name})")
                    results.append(DedupeResult(entry.path, dest_path, file_hash, True, False, True))
            except Exception as e:
                self._log_status(f"Error {action.lower()} {filename}: {e}")
                results.append(DedupeResult(entry.path, None, file_hash, True, False, False, error_message=str(e)))

        action_past = "deleted" if permanent_delete else "moved"
        if self.cancel_check and self.cancel_check():
            self._log_status(f"Operation cancelled: {moved_count} duplicate(s) {action_past}")
        else:
            error_count = len(scan_result.hash_errors) + sum(1 for r in results if r.is_duplicate and not r.moved)
            self._log_status(
                f"Complete: {len(scan_result.primary_map)} unique group(s), {moved_count} duplicate(s) {action_past}, {error_count} error(s)"
            )

        return results, scan_result.total_files, scan_result.unique_count, moved_count

    # ---------- Compare two folders (dedupe B against A, without touching A) ----------

    def scan_compare(self, reference_folder: str, target_folder: str, recursive: bool = True,
                      algorithm: str = "md5") -> ScanResult:
        """
        Scan target_folder for files that already exist (by content) in reference_folder.
        reference_folder is only ever read, never modified.
        """
        if not os.path.exists(reference_folder):
            raise ValueError(f"Reference folder does not exist: {reference_folder}")
        if not os.path.exists(target_folder):
            raise ValueError(f"Target folder does not exist: {target_folder}")

        self._log_status("Scanning reference folder (A)...")
        ref_paths = self._get_all_files(reference_folder, recursive)
        self._log_status("Scanning target folder (B)...")
        tgt_paths = self._get_all_files(target_folder, recursive)

        ref_entries = self._stat_entries(ref_paths)
        tgt_entries = self._stat_entries(tgt_paths)

        ref_sizes = {e.size for e in ref_entries if e.error is None}
        tgt_sizes = {e.size for e in tgt_entries if e.error is None}
        shared_sizes = ref_sizes & tgt_sizes

        ref_candidates = [e for e in ref_entries if e.error is None and e.size in shared_sizes]
        tgt_candidates = [e for e in tgt_entries if e.error is None and e.size in shared_sizes]

        self._log_status(
            f"Size pre-filter: {len(ref_candidates) + len(tgt_candidates)} of "
            f"{len(ref_entries) + len(tgt_entries)} file(s) share a size across the two folders"
        )

        if self.cancel_check and self.cancel_check():
            return ScanResult({}, {}, {}, 0, 0, "")

        self._log_status(f"Hashing reference folder ({algorithm.upper()})...")
        ref_errors = self._hash_entries(ref_candidates, algorithm, 0, 40)
        self._log_status(f"Hashing target folder ({algorithm.upper()})...")
        tgt_errors = self._hash_entries(tgt_candidates, algorithm, 40, 70)
        hash_errors = {**ref_errors, **tgt_errors}

        if self.cancel_check and self.cancel_check():
            self._log_status("Operation cancelled during hashing")
            return ScanResult({}, {}, {}, 0, 0, "")

        ref_by_hash: Dict[str, FileEntry] = {}
        for e in ref_candidates:
            if e.file_hash is not None and e.file_hash not in ref_by_hash:
                ref_by_hash[e.file_hash] = e

        groups: Dict[str, List[FileEntry]] = defaultdict(list)
        primary_map: Dict[str, FileEntry] = {}
        for e in tgt_candidates:
            if e.file_hash is not None and e.file_hash in ref_by_hash:
                groups[e.file_hash].append(e)
                primary_map[e.file_hash] = ref_by_hash[e.file_hash]

        duplicate_count = sum(len(es) for es in groups.values())
        unique_count = len(tgt_entries) - duplicate_count - len(tgt_errors)

        self._log_status(f"Found {duplicate_count} file(s) in target folder that already exist in reference folder")

        return ScanResult(dict(groups), primary_map, hash_errors, len(tgt_entries), unique_count, "")

    def execute_compare(self, scan_result: ScanResult, target_folder: str, permanent_delete: bool = False,
                         progress_start: int = 70, progress_end: int = 100) -> Tuple[List[DedupeResult], int, int, int]:
        """Move (or delete) target-folder files that match the reference folder. Reference is never touched."""
        dupes_folder = os.path.join(target_folder, "Dupes")
        if not permanent_delete:
            os.makedirs(dupes_folder, exist_ok=True)

        results: List[DedupeResult] = []
        duplicates: List[Tuple[str, FileEntry]] = []
        for file_hash, entries in scan_result.groups.items():
            for e in entries:
                duplicates.append((file_hash, e))

        duplicate_count = len(duplicates)
        action = "Deleting" if permanent_delete else "Moving"
        self._log_status(f"{action} {duplicate_count} file(s) from target folder that match the reference folder...")

        moved_count = 0
        for idx, (file_hash, entry) in enumerate(duplicates, 1):
            if self.cancel_check and self.cancel_check():
                self._log_status("Operation cancelled by user")
                break

            filename = os.path.basename(entry.path)
            progress = progress_start + int((idx / max(duplicate_count, 1)) * (progress_end - progress_start))
            self._report_progress(progress, 100, f"{action}: {filename}")

            try:
                if permanent_delete:
                    os.unlink(entry.path)
                    moved_count += 1
                    results.append(DedupeResult(entry.path, None, file_hash, True, False, True))
                else:
                    dest_path = self._get_unique_dest_path(dupes_folder, filename)
                    shutil.move(entry.path, dest_path)
                    moved_count += 1
                    self._log_status(f"Moved: {filename}")
                    results.append(DedupeResult(entry.path, dest_path, file_hash, True, False, True))
            except Exception as e:
                self._log_status(f"Error {action.lower()} {filename}: {e}")
                results.append(DedupeResult(entry.path, None, file_hash, True, False, False, error_message=str(e)))

        action_past = "deleted" if permanent_delete else "moved"
        if self.cancel_check and self.cancel_check():
            self._log_status(f"Operation cancelled: {moved_count} file(s) {action_past}")
        else:
            self._log_status(f"Complete: {moved_count} file(s) {action_past} from target folder")

        return results, scan_result.total_files, scan_result.unique_count, moved_count

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
