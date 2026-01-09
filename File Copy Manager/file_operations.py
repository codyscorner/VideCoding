"""File operation classes for File Copy Manager application"""

import os
import shutil
import time
import fnmatch
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from folder_organization import FolderOrganizer, FolderStructure


@dataclass
class FileOperationResult:
    """Result of a file operation"""
    success: bool
    source_file: str
    destination_file: Optional[str] = None
    error_message: Optional[str] = None
    file_size: int = 0
    copy_time: float = 0.0


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
    def get_files_with_patterns(folder_path: str, patterns: List[str], recursive: bool = False) -> List[tuple[str, str]]:
        """
        Get all files in a folder matching the given patterns

        Args:
            folder_path: Path to scan
            patterns: List of glob patterns to match (e.g., ["*.jpg", "*.png", "oct*.*"])
            recursive: If True, scan subdirectories

        Returns:
            List of (full_path, relative_path) tuples

        Raises:
            OSError: If folder cannot be read
        """
        files = []

        if recursive:
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    if FileScanner._matches_any_pattern(filename, patterns):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, folder_path)
                        files.append((full_path, rel_path))
        else:
            for filename in os.listdir(folder_path):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path) and FileScanner._matches_any_pattern(filename, patterns):
                    files.append((full_path, filename))

        return files


class FileCopier:
    """Handles file copying operations"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        folder_structure: FolderStructure = FolderStructure.FLAT,
        number_duplicates: bool = True,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None
    ):
        """
        Initialize the file copier

        Args:
            status_callback: Optional callback function for status updates
            folder_structure: Folder organization structure
            number_duplicates: If True, number duplicate files; if False, skip duplicates
            progress_callback: Optional callback for progress updates (current, total, filename, file_progress)
        """
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.validator = FileValidator()
        self.scanner = FileScanner()
        self.folder_structure = folder_structure
        self.number_duplicates = number_duplicates
        self.organizer = FolderOrganizer()

    def _log_status(self, message: str) -> None:
        """Log status message if callback is set"""
        if self.status_callback:
            self.status_callback(message)

    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted string (e.g., "1.23 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _apply_filters(
        self,
        files: List[tuple[str, str]],
        min_size_bytes: Optional[float],
        max_size_bytes: Optional[float],
        max_days_old: Optional[int]
    ) -> List[tuple[str, str]]:
        """
        Apply file filters to the file list

        Args:
            files: List of (full_path, rel_path) tuples
            min_size_bytes: Minimum file size
            max_size_bytes: Maximum file size
            max_days_old: Maximum file age in days

        Returns:
            Filtered list of files
        """
        if not any([min_size_bytes, max_size_bytes, max_days_old]):
            return files

        from datetime import datetime, timedelta

        filtered = []
        now = datetime.now()

        for full_path, rel_path in files:
            # Size filter
            if min_size_bytes is not None or max_size_bytes is not None:
                try:
                    file_size = os.path.getsize(full_path)
                    if min_size_bytes is not None and file_size < min_size_bytes:
                        continue
                    if max_size_bytes is not None and file_size > max_size_bytes:
                        continue
                except OSError:
                    continue

            # Date filter
            if max_days_old is not None:
                try:
                    mtime = os.path.getmtime(full_path)
                    file_date = datetime.fromtimestamp(mtime)
                    age_days = (now - file_date).days
                    if age_days > max_days_old:
                        continue
                except OSError:
                    continue

            filtered.append((full_path, rel_path))

        return filtered

    def copy_files(
        self,
        source_folder: str,
        dest_folder: str,
        file_mask: str,
        preserve_structure: bool = False,
        recursive: bool = True,
        min_size_bytes: Optional[float] = None,
        max_size_bytes: Optional[float] = None,
        max_days_old: Optional[int] = None
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
        os.makedirs(dest_folder, exist_ok=True)

        # Determine if we should use preserve mode
        structure = FolderStructure.PRESERVE if preserve_structure else self.folder_structure

        # Get files to process
        search_mode = "recursively" if recursive else "in root folder only"
        patterns_str = ", ".join(patterns)
        self._log_status(f"Scanning source folder {search_mode} for files matching: {patterns_str}")
        source_files = self.scanner.get_files_with_patterns(source_folder, patterns, recursive)

        if not source_files:
            self._log_status(f"No files found matching '{patterns_str}' in source folder")
            return []

        self._log_status(f"Found {len(source_files)} files to process")

        # Apply filters
        filtered_files = self._apply_filters(
            source_files,
            min_size_bytes,
            max_size_bytes,
            max_days_old
        )

        if len(filtered_files) < len(source_files):
            skipped = len(source_files) - len(filtered_files)
            self._log_status(f"Filtered out {skipped} files based on filter criteria")

        if not filtered_files:
            self._log_status("No files match the filter criteria")
            return []

        self._log_status(f"Processing {len(filtered_files)} files after filtering")

        # Process each file
        results = []
        for idx, (full_path, rel_path) in enumerate(filtered_files, 1):
            # Update progress
            if self.progress_callback:
                filename = os.path.basename(full_path)
                self.progress_callback(idx, len(filtered_files), filename, 0)

            result = self._process_single_file(
                full_path,
                rel_path,
                source_folder,
                dest_folder,
                structure
            )
            results.append(result)

            # Update progress to 100% for this file
            if self.progress_callback:
                self.progress_callback(idx, len(filtered_files), filename, 100)

        # Summary
        success_count = sum(1 for r in results if r.success)
        error_count = sum(1 for r in results if not r.success)
        self._log_status(f"Operation completed: {success_count} files copied, {error_count} errors")

        return results

    def _process_single_file(
        self,
        source_path: str,
        rel_path: str,
        source_root: str,
        dest_folder: str,
        structure: FolderStructure
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

        # Determine final filename (handle duplicates)
        dest_path = os.path.join(final_dest_folder, filename)
        final_filename = filename

        if os.path.exists(dest_path):
            if self.number_duplicates:
                # Add number to filename
                base_name, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    final_filename = f"{base_name}_{counter:03d}{ext}"
                    dest_path = os.path.join(final_dest_folder, final_filename)
                    counter += 1
                self._log_status(f"Duplicate found: {filename} → {final_filename}")
            else:
                # Skip duplicate
                self._log_status(f"Skipped (duplicate): {filename}")
                return FileOperationResult(
                    success=True,
                    source_file=filename,
                    destination_file=None,
                    error_message="Skipped (duplicate)"
                )

        try:
            # Get file size
            file_size = os.path.getsize(source_path)

            # Copy the file and measure time
            start_time = time.time()
            shutil.copy2(source_path, dest_path)
            copy_time = time.time() - start_time

            # Format file size
            size_str = self._format_file_size(file_size)
            time_str = f"{copy_time:.2f}s"

            # Log the operation
            if structure == FolderStructure.PRESERVE:
                rel_dest = os.path.relpath(dest_path, dest_folder)
                self._log_status(f"Copied: {rel_path} → {rel_dest} ({size_str}, {time_str})")
            else:
                subfolder_name = os.path.relpath(final_dest_folder, dest_folder)
                if subfolder_name == ".":
                    self._log_status(f"Copied: {filename} ({size_str}, {time_str})")
                else:
                    self._log_status(f"Copied: {filename} → {subfolder_name}{os.sep}{final_filename} ({size_str}, {time_str})")

            return FileOperationResult(
                success=True,
                source_file=filename,
                destination_file=final_filename,
                file_size=file_size,
                copy_time=copy_time
            )
        except Exception as e:
            error_msg = f"Error copying {filename}: {e}"
            self._log_status(error_msg)
            return FileOperationResult(
                success=False,
                source_file=filename,
                error_message=str(e)
            )
