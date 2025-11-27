"""File sorting strategies for File Rename Mover application"""

import os
from pathlib import Path
from typing import List, Callable
from enum import Enum
from datetime import datetime


class SortOrder(Enum):
    """Sort order enumeration"""
    ASCENDING = "asc"
    DESCENDING = "desc"


class SortBy(Enum):
    """Sort by field enumeration"""
    NAME = "name"
    DATE_MODIFIED = "date_modified"
    DATE_CREATED = "date_created"
    SIZE = "size"


class FileSorter:
    """Handles file sorting operations"""

    @staticmethod
    def sort_files(
        folder_path: str,
        filenames: List[str],
        sort_by: SortBy = SortBy.NAME,
        sort_order: SortOrder = SortOrder.ASCENDING
    ) -> List[str]:
        """
        Sort files by specified criteria

        Args:
            folder_path: Path to folder containing files
            filenames: List of filenames to sort
            sort_by: Field to sort by
            sort_order: Sort order (ascending or descending)

        Returns:
            Sorted list of filenames
        """
        if not filenames:
            return []

        # Get the sorting key function
        key_func = FileSorter._get_sort_key_function(folder_path, sort_by)

        # Sort files
        sorted_files = sorted(
            filenames,
            key=key_func,
            reverse=(sort_order == SortOrder.DESCENDING)
        )

        return sorted_files

    @staticmethod
    def _get_sort_key_function(folder_path: str, sort_by: SortBy) -> Callable:
        """
        Get the appropriate key function for sorting

        Args:
            folder_path: Path to folder containing files
            sort_by: Field to sort by

        Returns:
            Key function for sorting
        """
        if sort_by == SortBy.NAME:
            return lambda filename: filename.lower()

        elif sort_by == SortBy.DATE_MODIFIED:
            return lambda filename: FileSorter._get_file_mtime(folder_path, filename)

        elif sort_by == SortBy.DATE_CREATED:
            return lambda filename: FileSorter._get_file_ctime(folder_path, filename)

        elif sort_by == SortBy.SIZE:
            return lambda filename: FileSorter._get_file_size(folder_path, filename)

        else:
            # Default to name
            return lambda filename: filename.lower()

    @staticmethod
    def _get_file_mtime(folder_path: str, filename: str) -> float:
        """Get file modification time"""
        try:
            file_path = os.path.join(folder_path, filename)
            return os.path.getmtime(file_path)
        except OSError:
            return 0.0

    @staticmethod
    def _get_file_ctime(folder_path: str, filename: str) -> float:
        """Get file creation time"""
        try:
            file_path = os.path.join(folder_path, filename)
            return os.path.getctime(file_path)
        except OSError:
            return 0.0

    @staticmethod
    def _get_file_size(folder_path: str, filename: str) -> int:
        """Get file size in bytes"""
        try:
            file_path = os.path.join(folder_path, filename)
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def get_file_datetime(folder_path: str, filename: str, use_modified: bool = True) -> datetime:
        """
        Get file datetime

        Args:
            folder_path: Path to folder containing file
            filename: Filename
            use_modified: If True, use modification time; otherwise use creation time

        Returns:
            Datetime object
        """
        try:
            file_path = os.path.join(folder_path, filename)
            if use_modified:
                timestamp = os.path.getmtime(file_path)
            else:
                timestamp = os.path.getctime(file_path)
            return datetime.fromtimestamp(timestamp)
        except OSError:
            return datetime.now()
