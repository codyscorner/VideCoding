"""File operation classes for File Rename Mover application"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from sorting import FileSorter, SortBy, SortOrder
from rename_patterns import RenamePattern, NumberingPattern
from folder_organization import FolderOrganizer, FolderStructure


@dataclass
class FileOperationResult:
    """Result of a file operation"""
    success: bool
    source_file: str
    destination_file: Optional[str] = None
    error_message: Optional[str] = None


class FileValidator:
    """Validates file operations and inputs"""

    # Invalid characters for Windows filenames
    INVALID_FILENAME_CHARS = r'<>:"/\|?*'

    @staticmethod
    def validate_extension(extension: str) -> str:
        """
        Validate and normalize file extension

        Args:
            extension: File extension to validate

        Returns:
            Normalized extension with leading dot

        Raises:
            ValueError: If extension is empty or contains invalid characters
        """
        extension = extension.strip()
        if not extension:
            raise ValueError("Extension cannot be empty")

        if not extension.startswith('.'):
            extension = '.' + extension

        # Check for invalid characters (excluding the dot)
        ext_without_dot = extension[1:]
        if any(char in FileValidator.INVALID_FILENAME_CHARS for char in ext_without_dot):
            raise ValueError(f"Extension contains invalid characters: {extension}")

        return extension

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

    @staticmethod
    def validate_rename_pattern(pattern: str) -> None:
        """
        Validate rename pattern (base name)

        Args:
            pattern: Pattern to validate

        Raises:
            ValueError: If pattern is empty, contains invalid characters, or has path traversal
        """
        if not pattern.strip():
            raise ValueError("Rename pattern cannot be empty")

        pattern = pattern.strip()

        # Check for path traversal attempts
        if '..' in pattern:
            raise ValueError("Rename pattern cannot contain '..' (path traversal)")

        # Check for path separators
        if '/' in pattern or '\\' in pattern:
            raise ValueError("Rename pattern cannot contain path separators (/ or \\)")

        # Check for other invalid filename characters
        invalid_chars = set(FileValidator.INVALID_FILENAME_CHARS) - {'/', '\\'}  # Already checked
        if any(char in invalid_chars for char in pattern):
            invalid_found = [char for char in pattern if char in invalid_chars]
            raise ValueError(f"Rename pattern contains invalid characters: {', '.join(invalid_found)}")

        # Check for reserved Windows names
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        if pattern.upper() in reserved_names:
            raise ValueError(f"Rename pattern cannot be a reserved Windows name: {pattern}")


class FileScanner:
    """Scans directories for files matching criteria"""

    @staticmethod
    def get_files_with_extension(folder_path: str, extension: str) -> List[str]:
        """
        Get all files in a folder with a specific extension

        Args:
            folder_path: Path to scan
            extension: File extension to match (with or without dot)

        Returns:
            List of filenames matching the extension

        Raises:
            OSError: If folder cannot be read
        """
        if not extension.startswith('.'):
            extension = '.' + extension

        files = []
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(extension.lower()):
                files.append(filename)

        return files

    @staticmethod
    def get_max_counter(folder_path: str, base_name: str, extension: str, padding: int = 6) -> int:
        """
        Scan destination folder for existing files and find the highest counter

        Args:
            folder_path: Folder to scan
            base_name: Base name pattern to match
            extension: File extension to match
            padding: Number of digits in the counter (default 6)

        Returns:
            Highest counter found (0 if none found)
        """
        max_counter = 0
        # Match pattern: basename_NNNNNN.ext (where N is any digit)
        # Use \d+ to match any number of digits for flexibility
        pattern = rf"^{re.escape(base_name)}_(\d+){re.escape(extension)}$"

        try:
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    match = re.match(pattern, filename, re.IGNORECASE)
                    if match:
                        counter = int(match.group(1))
                        max_counter = max(max_counter, counter)
        except OSError:
            pass

        return max_counter


class FileRenamer:
    """Handles file renaming and moving operations"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        rename_pattern: Optional[RenamePattern] = None,
        sort_by: SortBy = SortBy.NAME,
        sort_order: SortOrder = SortOrder.ASCENDING,
        folder_structure: FolderStructure = FolderStructure.FLAT
    ):
        """
        Initialize the file renamer

        Args:
            status_callback: Optional callback function for status updates
            rename_pattern: Rename pattern to use (default: NumberingPattern)
            sort_by: Field to sort files by
            sort_order: Sort order (ascending or descending)
            folder_structure: Folder organization structure
        """
        self.status_callback = status_callback
        self.validator = FileValidator()
        self.scanner = FileScanner()
        self.rename_pattern = rename_pattern or NumberingPattern()
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.folder_structure = folder_structure
        self.sorter = FileSorter()
        self.organizer = FolderOrganizer()

    def _log_status(self, message: str) -> None:
        """Log status message if callback is set"""
        if self.status_callback:
            self.status_callback(message)

    def move_and_rename(
        self,
        source_folder: str,
        dest_folder: str,
        extension: str,
        base_name: str
    ) -> List[FileOperationResult]:
        """
        Move and rename files from source to destination

        Args:
            source_folder: Source folder path
            dest_folder: Destination folder path
            extension: File extension to process
            base_name: Base name for renaming files

        Returns:
            List of FileOperationResult objects

        Raises:
            ValueError: If validation fails
            OSError: If folders cannot be accessed
        """
        # Validate inputs
        self.validator.validate_folder_exists(source_folder)
        extension = self.validator.validate_extension(extension)
        self.validator.validate_rename_pattern(base_name)

        # Create destination folder if it doesn't exist
        os.makedirs(dest_folder, exist_ok=True)

        # Get files to process
        self._log_status(f"Scanning source folder for {extension} files...")
        source_files = self.scanner.get_files_with_extension(source_folder, extension)

        if not source_files:
            self._log_status(f"No files found with extension '{extension}' in source folder")
            return []

        self._log_status(f"Found {len(source_files)} files to process")

        # Sort files
        self._log_status(f"Sorting files by {self.sort_by.value} ({self.sort_order.value})...")
        sorted_files = self.sorter.sort_files(
            source_folder,
            source_files,
            self.sort_by,
            self.sort_order
        )

        # Get starting counter by scanning destination for existing files
        max_existing = self.scanner.get_max_counter(dest_folder, base_name, extension)
        counter = max_existing + 1
        if max_existing > 0:
            self._log_status(f"Found existing files up to {base_name}_{str(max_existing).zfill(6)}{extension}, starting at {counter}")

        # Process each file
        results = []
        for filename in sorted_files:
            result = self._process_single_file(
                source_folder,
                dest_folder,
                filename,
                base_name,
                extension,
                counter
            )
            results.append(result)

            if result.success:
                counter += 1

        # Summary
        success_count = sum(1 for r in results if r.success)
        error_count = sum(1 for r in results if not r.success)
        self._log_status(f"Operation completed: {success_count} files moved, {error_count} errors")

        return results

    def _process_single_file(
        self,
        source_folder: str,
        dest_folder: str,
        filename: str,
        base_name: str,
        extension: str,
        counter: int
    ) -> FileOperationResult:
        """
        Process a single file

        Args:
            source_folder: Source folder path
            dest_folder: Destination folder path
            filename: Name of file to process
            base_name: Base name for renaming
            extension: File extension
            counter: Current counter value

        Returns:
            FileOperationResult object
        """
        source_path = os.path.join(source_folder, filename)

        # Generate new filename using pattern
        new_filename = self.rename_pattern.generate_filename(
            base_name,
            extension,
            counter,
            source_path
        )

        # Determine destination folder with organization
        subfolder = self.organizer.get_destination_subfolder(
            source_path,
            self.folder_structure,
            use_file_date=True
        )

        # Create destination path
        if subfolder:
            final_dest_folder = self.organizer.create_folder_structure(dest_folder, subfolder)
        else:
            final_dest_folder = dest_folder

        dest_path = os.path.join(final_dest_folder, new_filename)

        try:
            # Check if source and destination are the same
            if os.path.abspath(source_path) == os.path.abspath(dest_path):
                self._log_status(f"Skipped: {filename} (already has target name)")
                return FileOperationResult(
                    success=True,
                    source_file=filename,
                    destination_file=new_filename
                )

            # Check if destination already exists
            if os.path.exists(dest_path):
                error_msg = f"Destination already exists: {new_filename}"
                self._log_status(error_msg)
                return FileOperationResult(
                    success=False,
                    source_file=filename,
                    error_message=error_msg
                )

            # Move/rename the file
            shutil.move(source_path, dest_path)

            # Log the operation
            if subfolder:
                self._log_status(f"Moved: {filename} → {subfolder}{os.sep}{new_filename}")
            else:
                # Check if it was a move or just a rename
                if os.path.dirname(source_path) == final_dest_folder:
                    self._log_status(f"Renamed: {filename} → {new_filename}")
                else:
                    self._log_status(f"Moved: {filename} → {new_filename}")

            return FileOperationResult(
                success=True,
                source_file=filename,
                destination_file=new_filename
            )
        except Exception as e:
            error_msg = f"Error processing {filename}: {e}"
            self._log_status(error_msg)
            return FileOperationResult(
                success=False,
                source_file=filename,
                error_message=str(e)
            )

    def generate_preview(
        self,
        source_folder: str,
        extension: str,
        base_name: str,
        dest_folder: Optional[str] = None
    ) -> List[tuple[str, str]]:
        """
        Generate a preview of what files would be renamed to

        Args:
            source_folder: Source folder path
            extension: File extension to process
            base_name: Base name for renaming files
            dest_folder: Optional destination folder to check for existing files

        Returns:
            List of (original_name, new_name) tuples
        """
        extension = self.validator.validate_extension(extension)
        source_files = self.scanner.get_files_with_extension(source_folder, extension)

        if not source_files:
            return []

        # Sort files using current sorting configuration
        sorted_files = self.sorter.sort_files(
            source_folder,
            source_files,
            self.sort_by,
            self.sort_order
        )

        # Get starting counter by checking destination folder for existing files
        counter = 1
        if dest_folder and os.path.exists(dest_folder):
            max_existing = self.scanner.get_max_counter(dest_folder, base_name, extension)
            counter = max_existing + 1

        # Generate preview using current pattern
        preview = []
        for filename in sorted_files:
            source_path = os.path.join(source_folder, filename)
            new_filename = self.rename_pattern.generate_filename(
                base_name,
                extension,
                counter,
                source_path
            )
            preview.append((filename, new_filename))
            counter += 1

        return preview
