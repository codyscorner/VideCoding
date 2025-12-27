"""File operation classes for File Copy Manager application"""

import os
import shutil
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


class FileValidator:
    """Validates file operations and inputs"""

    @staticmethod
    def validate_extension(extension: str) -> str:
        """
        Validate and normalize file extension

        Args:
            extension: File extension to validate

        Returns:
            Normalized extension with leading dot

        Raises:
            ValueError: If extension is empty
        """
        extension = extension.strip()
        if not extension:
            raise ValueError("Extension cannot be empty")

        if not extension.startswith('.'):
            extension = '.' + extension

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


class FileScanner:
    """Scans directories for files matching criteria"""

    @staticmethod
    def get_files_with_extension(folder_path: str, extension: str, recursive: bool = False) -> List[tuple[str, str]]:
        """
        Get all files in a folder with a specific extension

        Args:
            folder_path: Path to scan
            extension: File extension to match (with or without dot)
            recursive: If True, scan subdirectories

        Returns:
            List of (full_path, relative_path) tuples

        Raises:
            OSError: If folder cannot be read
        """
        if not extension.startswith('.'):
            extension = '.' + extension

        files = []

        if recursive:
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    if filename.lower().endswith(extension.lower()):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, folder_path)
                        files.append((full_path, rel_path))
        else:
            for filename in os.listdir(folder_path):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path) and filename.lower().endswith(extension.lower()):
                    files.append((full_path, filename))

        return files


class FileCopier:
    """Handles file copying operations"""

    def __init__(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        folder_structure: FolderStructure = FolderStructure.FLAT,
        number_duplicates: bool = True
    ):
        """
        Initialize the file copier

        Args:
            status_callback: Optional callback function for status updates
            folder_structure: Folder organization structure
            number_duplicates: If True, number duplicate files; if False, skip duplicates
        """
        self.status_callback = status_callback
        self.validator = FileValidator()
        self.scanner = FileScanner()
        self.folder_structure = folder_structure
        self.number_duplicates = number_duplicates
        self.organizer = FolderOrganizer()

    def _log_status(self, message: str) -> None:
        """Log status message if callback is set"""
        if self.status_callback:
            self.status_callback(message)

    def copy_files(
        self,
        source_folder: str,
        dest_folder: str,
        extension: str,
        preserve_structure: bool = False
    ) -> List[FileOperationResult]:
        """
        Copy files from source to destination

        Args:
            source_folder: Source folder path
            dest_folder: Destination folder path
            extension: File extension to process
            preserve_structure: If True, preserve original folder structure

        Returns:
            List of FileOperationResult objects

        Raises:
            ValueError: If validation fails
            OSError: If folders cannot be accessed
        """
        # Validate inputs
        self.validator.validate_folder_exists(source_folder)
        extension = self.validator.validate_extension(extension)

        # Create destination folder if it doesn't exist
        os.makedirs(dest_folder, exist_ok=True)

        # Determine if we should use preserve mode
        structure = FolderStructure.PRESERVE if preserve_structure else self.folder_structure

        # Get files to process
        self._log_status(f"Scanning source folder for {extension} files...")
        recursive = preserve_structure
        source_files = self.scanner.get_files_with_extension(source_folder, extension, recursive)

        if not source_files:
            self._log_status(f"No files found with extension '{extension}' in source folder")
            return []

        self._log_status(f"Found {len(source_files)} files to process")

        # Process each file
        results = []
        for full_path, rel_path in source_files:
            result = self._process_single_file(
                full_path,
                rel_path,
                source_folder,
                dest_folder,
                structure
            )
            results.append(result)

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
            # Copy the file
            shutil.copy2(source_path, dest_path)

            # Log the operation
            if structure == FolderStructure.PRESERVE:
                rel_dest = os.path.relpath(dest_path, dest_folder)
                self._log_status(f"Copied: {rel_path} → {rel_dest}")
            else:
                subfolder_name = os.path.relpath(final_dest_folder, dest_folder)
                if subfolder_name == ".":
                    self._log_status(f"Copied: {filename}")
                else:
                    self._log_status(f"Copied: {filename} → {subfolder_name}{os.sep}{final_filename}")

            return FileOperationResult(
                success=True,
                source_file=filename,
                destination_file=final_filename
            )
        except Exception as e:
            error_msg = f"Error copying {filename}: {e}"
            self._log_status(error_msg)
            return FileOperationResult(
                success=False,
                source_file=filename,
                error_message=str(e)
            )
