"""Rename pattern strategies for File Rename Mover application"""

from datetime import datetime
from typing import Optional
from enum import Enum
import os


class PatternType(Enum):
    """Rename pattern types"""
    NUMBERING = "numbering"
    DATETIME = "datetime"
    PREFIX = "prefix"
    CUSTOM = "custom"


class DateTimeFormat(Enum):
    """DateTime format options"""
    YYYYMMDD = "%Y%m%d"
    YYYY_MM_DD = "%Y-%m-%d"
    YYYYMMDD_HHMMSS = "%Y%m%d_%H%M%S"
    YYYY_MM_DD_HH_MM_SS = "%Y-%m-%d_%H-%M-%S"
    MMDDYYYY = "%m%d%Y"
    DDMMYYYY = "%d%m%Y"


class RenamePattern:
    """Base class for rename patterns"""

    def generate_filename(
        self,
        base_name: str,
        extension: str,
        counter: int,
        file_path: Optional[str] = None
    ) -> str:
        """
        Generate a filename based on the pattern

        Args:
            base_name: Base name for the file
            extension: File extension
            counter: Counter for sequential numbering
            file_path: Optional path to original file (for datetime extraction)

        Returns:
            Generated filename
        """
        raise NotImplementedError


class NumberingPattern(RenamePattern):
    """Simple numbering pattern: basename_000001.ext"""

    def __init__(self, padding: int = 6):
        """
        Initialize numbering pattern

        Args:
            padding: Number of digits for counter (default 6)
        """
        self.padding = padding

    def generate_filename(
        self,
        base_name: str,
        extension: str,
        counter: int,
        file_path: Optional[str] = None
    ) -> str:
        """Generate filename with numbering"""
        counter_str = str(counter).zfill(self.padding)
        return f"{base_name}_{counter_str}{extension}"


class DateTimePattern(RenamePattern):
    """DateTime pattern: basename_YYYYMMDD_000001.ext"""

    def __init__(
        self,
        datetime_format: DateTimeFormat = DateTimeFormat.YYYYMMDD,
        include_counter: bool = True,
        use_file_date: bool = True,
        padding: int = 6
    ):
        """
        Initialize datetime pattern

        Args:
            datetime_format: Format for datetime string
            include_counter: Whether to include counter in filename
            use_file_date: If True, use file's date; otherwise use current date
            padding: Number of digits for counter
        """
        self.datetime_format = datetime_format
        self.include_counter = include_counter
        self.use_file_date = use_file_date
        self.padding = padding

    def generate_filename(
        self,
        base_name: str,
        extension: str,
        counter: int,
        file_path: Optional[str] = None
    ) -> str:
        """Generate filename with datetime"""
        # Get datetime
        if self.use_file_date and file_path and os.path.exists(file_path):
            timestamp = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.now()

        # Format datetime
        dt_str = dt.strftime(self.datetime_format.value)

        # Build filename
        if self.include_counter:
            counter_str = str(counter).zfill(self.padding)
            return f"{base_name}_{dt_str}_{counter_str}{extension}"
        else:
            return f"{base_name}_{dt_str}{extension}"


class PrefixPattern(RenamePattern):
    """Prefix pattern: prefix_originalname.ext"""

    def __init__(self, prefix: str, keep_original_name: bool = True):
        """
        Initialize prefix pattern

        Args:
            prefix: Prefix to add to filename
            keep_original_name: Whether to keep original filename
        """
        self.prefix = prefix
        self.keep_original_name = keep_original_name

    def generate_filename(
        self,
        base_name: str,
        extension: str,
        counter: int,
        file_path: Optional[str] = None
    ) -> str:
        """Generate filename with prefix"""
        if self.keep_original_name and file_path:
            original_name = os.path.splitext(os.path.basename(file_path))[0]
            return f"{self.prefix}_{original_name}{extension}"
        else:
            counter_str = str(counter).zfill(6)
            return f"{self.prefix}_{base_name}_{counter_str}{extension}"


class CustomPattern(RenamePattern):
    """Custom pattern with placeholders"""

    PLACEHOLDERS = {
        '{counter}': 'counter',
        '{date}': 'date',
        '{time}': 'time',
        '{datetime}': 'datetime',
        '{year}': 'year',
        '{month}': 'month',
        '{day}': 'day',
        '{original}': 'original'
    }

    def __init__(self, pattern_string: str, padding: int = 6):
        """
        Initialize custom pattern

        Args:
            pattern_string: Pattern string with placeholders
            padding: Number of digits for counter

        Example patterns:
            - "{year}-{month}-{day}_{counter}" -> "2025-11-27_000001"
            - "{date}_{original}" -> "20251127_photo"
            - "IMG_{counter}_{datetime}" -> "IMG_000001_20251127_143022"
        """
        self.pattern_string = pattern_string
        self.padding = padding

    def generate_filename(
        self,
        base_name: str,
        extension: str,
        counter: int,
        file_path: Optional[str] = None
    ) -> str:
        """Generate filename with custom pattern"""
        # Get datetime
        if file_path and os.path.exists(file_path):
            timestamp = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.now()

        # Get original name if available
        original_name = base_name
        if file_path:
            original_name = os.path.splitext(os.path.basename(file_path))[0]

        # Replace placeholders
        result = self.pattern_string
        result = result.replace('{counter}', str(counter).zfill(self.padding))
        result = result.replace('{date}', dt.strftime('%Y%m%d'))
        result = result.replace('{time}', dt.strftime('%H%M%S'))
        result = result.replace('{datetime}', dt.strftime('%Y%m%d_%H%M%S'))
        result = result.replace('{year}', dt.strftime('%Y'))
        result = result.replace('{month}', dt.strftime('%m'))
        result = result.replace('{day}', dt.strftime('%d'))
        result = result.replace('{original}', original_name)

        return f"{result}{extension}"


class PatternFactory:
    """Factory for creating rename patterns"""

    @staticmethod
    def create_pattern(
        pattern_type: PatternType,
        **kwargs
    ) -> RenamePattern:
        """
        Create a rename pattern

        Args:
            pattern_type: Type of pattern to create
            **kwargs: Additional arguments for pattern

        Returns:
            RenamePattern instance
        """
        if pattern_type == PatternType.NUMBERING:
            return NumberingPattern(
                padding=kwargs.get('padding', 6)
            )

        elif pattern_type == PatternType.DATETIME:
            return DateTimePattern(
                datetime_format=kwargs.get('datetime_format', DateTimeFormat.YYYYMMDD),
                include_counter=kwargs.get('include_counter', True),
                use_file_date=kwargs.get('use_file_date', True),
                padding=kwargs.get('padding', 6)
            )

        elif pattern_type == PatternType.PREFIX:
            return PrefixPattern(
                prefix=kwargs.get('prefix', 'file'),
                keep_original_name=kwargs.get('keep_original_name', True)
            )

        elif pattern_type == PatternType.CUSTOM:
            return CustomPattern(
                pattern_string=kwargs.get('pattern_string', '{counter}'),
                padding=kwargs.get('padding', 6)
            )

        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
