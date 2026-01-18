"""Image utilities for loading, thumbnails, and metadata extraction"""

from PIL import Image
from pathlib import Path
from typing import Tuple, Optional, List, Set
from dataclasses import dataclass
import os

SUPPORTED_EXTENSIONS: Set[str] = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'
}


@dataclass
class ImageMetadata:
    """Metadata for an image file"""
    path: str
    filename: str
    width: int
    height: int
    file_size: int  # bytes
    modified_time: float  # Unix timestamp
    format: str  # e.g., "JPEG", "PNG"

    @property
    def resolution(self) -> Tuple[int, int]:
        """Get resolution as tuple"""
        return (self.width, self.height)

    @property
    def megapixels(self) -> float:
        """Get megapixels"""
        return (self.width * self.height) / 1_000_000


class ImageUtils:
    """Utilities for image handling"""

    @staticmethod
    def is_supported_extension(file_path: str) -> bool:
        """Check if file has a supported image extension"""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def is_valid_image(file_path: str) -> bool:
        """
        Check if file is a valid, supported image

        Args:
            file_path: Path to the image file

        Returns:
            True if file is a valid image, False otherwise
        """
        if not ImageUtils.is_supported_extension(file_path):
            return False

        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    @staticmethod
    def get_image_metadata(file_path: str) -> Optional[ImageMetadata]:
        """
        Extract metadata from image file

        Args:
            file_path: Path to the image file

        Returns:
            ImageMetadata object or None if image cannot be read
        """
        try:
            path = Path(file_path)
            stat = path.stat()

            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format or "Unknown"

            return ImageMetadata(
                path=str(path.absolute()),
                filename=path.name,
                width=width,
                height=height,
                file_size=stat.st_size,
                modified_time=stat.st_mtime,
                format=img_format
            )
        except Exception:
            return None

    @staticmethod
    def create_thumbnail(
        file_path: str,
        size: Tuple[int, int] = (150, 150)
    ) -> Optional[Image.Image]:
        """
        Create thumbnail preserving aspect ratio

        Args:
            file_path: Path to the image file
            size: Maximum size (width, height) for thumbnail

        Returns:
            PIL Image or None on failure
        """
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary (for PNG with alpha, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Create thumbnail (modifies in place, preserves aspect ratio)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img.copy()
        except Exception:
            return None

    @staticmethod
    def meets_resolution_filter(
        file_path: str,
        min_resolution: Tuple[int, int]
    ) -> bool:
        """
        Check if image meets minimum resolution requirements

        Args:
            file_path: Path to the image file
            min_resolution: Minimum (width, height) required

        Returns:
            True if image meets minimum resolution
        """
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                return width >= min_resolution[0] and height >= min_resolution[1]
        except Exception:
            return False

    @staticmethod
    def scan_directory(
        directory: str,
        recursive: bool = True,
        excluded_dirs: Optional[List[str]] = None,
        min_resolution: Optional[Tuple[int, int]] = None
    ) -> List[str]:
        """
        Scan directory for valid image files

        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            excluded_dirs: List of directory names to exclude
            min_resolution: Optional minimum resolution filter

        Returns:
            List of absolute paths to valid images
        """
        excluded = set(excluded_dirs or [])
        image_paths = []
        directory_path = Path(directory)

        if not directory_path.exists() or not directory_path.is_dir():
            return []

        if recursive:
            for root, dirs, files in os.walk(directory_path):
                # Remove excluded directories from dirs to prevent walking into them
                dirs[:] = [d for d in dirs if d not in excluded]

                for file in files:
                    file_path = os.path.join(root, file)
                    if ImageUtils.is_supported_extension(file_path):
                        # Apply resolution filter if specified
                        if min_resolution is not None:
                            if not ImageUtils.meets_resolution_filter(file_path, min_resolution):
                                continue
                        image_paths.append(str(Path(file_path).absolute()))
        else:
            for file in directory_path.iterdir():
                if file.is_file() and ImageUtils.is_supported_extension(str(file)):
                    file_path = str(file.absolute())
                    if min_resolution is not None:
                        if not ImageUtils.meets_resolution_filter(file_path, min_resolution):
                            continue
                    image_paths.append(file_path)

        return sorted(image_paths)

    @staticmethod
    def compare_quality(path1: str, path2: str) -> int:
        """
        Compare image quality/resolution

        Args:
            path1: Path to first image
            path2: Path to second image

        Returns:
            1 if path1 is better, -1 if path2 is better, 0 if equal
        """
        meta1 = ImageUtils.get_image_metadata(path1)
        meta2 = ImageUtils.get_image_metadata(path2)

        if meta1 is None and meta2 is None:
            return 0
        if meta1 is None:
            return -1
        if meta2 is None:
            return 1

        # Compare by megapixels first
        mp1 = meta1.megapixels
        mp2 = meta2.megapixels

        if mp1 > mp2 * 1.1:  # 10% tolerance
            return 1
        elif mp2 > mp1 * 1.1:
            return -1

        # If similar resolution, compare file size (larger often means better quality)
        if meta1.file_size > meta2.file_size * 1.1:
            return 1
        elif meta2.file_size > meta1.file_size * 1.1:
            return -1

        return 0

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable form

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
