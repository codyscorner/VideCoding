"""Core rename-and-copy logic for Bulk File Randomizer"""

import random
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

_CHARS = string.ascii_letters + string.digits  # a-z A-Z 0-9


def _random_suffix(length: int = 10) -> str:
    return "".join(random.choices(_CHARS, k=length))


def _unique_name(dest_dir: Path, prefix: str, suffix: str, ext: str) -> str:
    """Generate a name that does not already exist in dest_dir."""
    for _ in range(1000):
        name = f"{prefix}_{suffix}{ext}"
        if not (dest_dir / name).exists():
            return name
        suffix = _random_suffix()
    raise RuntimeError("Could not generate a unique filename after 1000 attempts")


@dataclass
class RenameResult:
    source: Path
    destination: Optional[Path]
    success: bool
    error: str = ""


def collect_files(
    source_dir: Path,
    masks: List[str],
    recursive: bool,
) -> List[Path]:
    """Return all files matching any mask pattern."""
    files: List[Path] = []
    glob_fn = source_dir.rglob if recursive else source_dir.glob
    seen: set = set()
    for mask in masks:
        mask = mask.strip()
        if not mask:
            continue
        for p in glob_fn(mask):
            if p.is_file() and p not in seen:
                seen.add(p)
                files.append(p)
    files.sort()
    return files


def copy_and_rename(
    source_dir: Path,
    prefix: str,
    masks: List[str],
    recursive: bool,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[RenameResult]:
    """
    Copy files from source_dir into source_dir/{prefix}/ with randomised names.
    Returns one RenameResult per file found.
    """
    dest_dir = source_dir / prefix
    dest_dir.mkdir(exist_ok=True)

    files = collect_files(source_dir, masks, recursive)
    results: List[RenameResult] = []
    total = len(files)

    for i, src in enumerate(files):
        if cancel_check and cancel_check():
            break

        # Skip files that are already inside dest_dir to avoid self-copy loops
        try:
            src.relative_to(dest_dir)
            continue
        except ValueError:
            pass

        if progress_cb:
            progress_cb(i, total, src.name)

        try:
            ext = src.suffix.lower()
            new_name = _unique_name(dest_dir, prefix, _random_suffix(), ext)
            dst = dest_dir / new_name
            shutil.copy2(src, dst)
            results.append(RenameResult(source=src, destination=dst, success=True))
        except Exception as exc:
            results.append(RenameResult(source=src, destination=None, success=False, error=str(exc)))

    if progress_cb:
        progress_cb(total, total, "")

    return results
