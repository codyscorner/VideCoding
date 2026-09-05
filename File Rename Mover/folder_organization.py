"""Folder organization strategies for File Rename Mover application"""

import os
from datetime import datetime
from enum import Enum
from typing import Optional


class FolderStructure(Enum):
    """Folder organization structures"""
    FLAT = "flat"  # No subfolders
    BY_YEAR = "year"  # YYYY/
    BY_YEAR_MONTH = "year_month"  # YYYY/MM/
    BY_YEAR_MONTH_DAY = "year_month_day"  # YYYY/MM/DD/
    BY_DATE = "date"  # YYYY-MM-DD/
    BY_MONTH = "month"  # YYYY-MM/


class FolderOrganizer:
    """Handles folder organization based on file dates"""

    @staticmethod
    def get_destination_subfolder(
        file_path: str,
        structure: FolderStructure,
        use_file_date: bool = True,
        base_name_folder: Optional[str] = None
    ) -> str:
        """
        Get the subfolder path based on organization structure

        Args:
            file_path: Path to the file
            structure: Folder structure to use
            use_file_date: If True, use file's date; otherwise use current date
            base_name_folder: If given, a folder with this name is placed in front of
                the date structure, e.g. ``Basename/YYYY/MM/DD``

        Returns:
            Relative subfolder path (empty string for flat structure without a
            base-name folder)
        """
        date_part = FolderOrganizer._get_date_subfolder(file_path, structure, use_file_date)
        prefix = (base_name_folder or "").strip()
        if prefix and date_part:
            return os.path.join(prefix, date_part)
        return prefix or date_part

    @staticmethod
    def _get_date_subfolder(
        file_path: str,
        structure: FolderStructure,
        use_file_date: bool = True
    ) -> str:
        """Date-only part of the subfolder path (no base-name folder)."""
        if structure == FolderStructure.FLAT:
            return ""

        # Get datetime
        if use_file_date and os.path.exists(file_path):
            timestamp = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.now()

        # Generate subfolder based on structure
        if structure == FolderStructure.BY_YEAR:
            return dt.strftime("%Y")

        elif structure == FolderStructure.BY_YEAR_MONTH:
            return os.path.join(dt.strftime("%Y"), dt.strftime("%m"))

        elif structure == FolderStructure.BY_YEAR_MONTH_DAY:
            return os.path.join(
                dt.strftime("%Y"),
                dt.strftime("%m"),
                dt.strftime("%d")
            )

        elif structure == FolderStructure.BY_DATE:
            return dt.strftime("%Y-%m-%d")

        elif structure == FolderStructure.BY_MONTH:
            return dt.strftime("%Y-%m")

        else:
            return ""

    @staticmethod
    def create_folder_structure(
        base_path: str,
        subfolder: str
    ) -> str:
        """
        Create folder structure and return full path

        Args:
            base_path: Base destination path
            subfolder: Relative subfolder path

        Returns:
            Full path to destination folder

        Raises:
            OSError: If folder cannot be created
        """
        if not subfolder:
            return base_path

        full_path = os.path.join(base_path, subfolder)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    @staticmethod
    def get_folder_structure_example(
        structure: FolderStructure,
        base_name_folder: Optional[str] = None
    ) -> str:
        """
        Get an example of the folder structure

        Args:
            structure: Folder structure type
            base_name_folder: Optional base-name folder shown in front of the date part

        Returns:
            Example string
        """
        dt = datetime(2025, 11, 27, 14, 30, 0)
        sep = os.sep  # Use OS-specific separator (\ for Windows, / for Unix)

        if structure == FolderStructure.BY_YEAR:
            date_part = dt.strftime('%Y')
        elif structure == FolderStructure.BY_YEAR_MONTH:
            date_part = f"{dt.strftime('%Y')}{sep}{dt.strftime('%m')}"
        elif structure == FolderStructure.BY_YEAR_MONTH_DAY:
            date_part = f"{dt.strftime('%Y')}{sep}{dt.strftime('%m')}{sep}{dt.strftime('%d')}"
        elif structure == FolderStructure.BY_DATE:
            date_part = dt.strftime('%Y-%m-%d')
        elif structure == FolderStructure.BY_MONTH:
            date_part = dt.strftime('%Y-%m')
        else:
            date_part = ""

        parts = ["dest_folder"]
        prefix = (base_name_folder or "").strip()
        if prefix:
            parts.append(prefix)
        if date_part:
            parts.append(date_part)
        return sep.join(parts) + sep
