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
        use_file_date: bool = True
    ) -> str:
        """
        Get the subfolder path based on organization structure

        Args:
            file_path: Path to the file
            structure: Folder structure to use
            use_file_date: If True, use file's date; otherwise use current date

        Returns:
            Relative subfolder path (empty string for flat structure)
        """
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
    def get_folder_structure_example(structure: FolderStructure) -> str:
        """
        Get an example of the folder structure

        Args:
            structure: Folder structure type

        Returns:
            Example string
        """
        dt = datetime(2025, 11, 27, 14, 30, 0)
        sep = os.sep  # Use OS-specific separator (\ for Windows, / for Unix)

        if structure == FolderStructure.FLAT:
            return f"dest_folder{sep}"

        elif structure == FolderStructure.BY_YEAR:
            return f"dest_folder{sep}{dt.strftime('%Y')}{sep}"

        elif structure == FolderStructure.BY_YEAR_MONTH:
            return f"dest_folder{sep}{dt.strftime('%Y')}{sep}{dt.strftime('%m')}{sep}"

        elif structure == FolderStructure.BY_YEAR_MONTH_DAY:
            return f"dest_folder{sep}{dt.strftime('%Y')}{sep}{dt.strftime('%m')}{sep}{dt.strftime('%d')}{sep}"

        elif structure == FolderStructure.BY_DATE:
            return f"dest_folder{sep}{dt.strftime('%Y-%m-%d')}{sep}"

        elif structure == FolderStructure.BY_MONTH:
            return f"dest_folder{sep}{dt.strftime('%Y-%m')}{sep}"

        else:
            return f"dest_folder{sep}"
