"""
core/scanner.py — Recursively find image files in a folder.
"""
from pathlib import Path
from typing import List

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def scan_folder(folder: str) -> List[Path]:
    """Return a sorted list of image Paths found recursively under *folder*."""
    root = Path(folder)
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
