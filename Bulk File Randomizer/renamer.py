"""Core rename-and-copy/move logic for Bulk File Randomizer"""

import random
import shutil
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

_CHARS = string.ascii_letters + string.digits  # a-z A-Z 0-9


def _random_suffix(rng: random.Random, length: int = 10) -> str:
    return "".join(rng.choices(_CHARS, k=length))


def _is_inside(path: Path, folder: Path) -> bool:
    try:
        path.relative_to(folder)
        return True
    except ValueError:
        return False


def make_rng(seed: Optional[int]) -> random.Random:
    """A dedicated Random instance so seeding never touches global random state."""
    return random.Random(seed) if seed is not None else random.Random()


def generate_batch_names(
    files: List[Path],
    prefix: str,
    dest_dir: Path,
    rng: random.Random,
) -> List[str]:
    """
    Assign a unique randomised name to each file, avoiding collisions with
    both existing files in dest_dir and names already assigned in this batch.
    Same files + same prefix + same seed always produces the same names —
    this is what makes preview and the actual run match exactly.
    """
    used: set = set()
    if dest_dir.exists():
        used.update(p.name for p in dest_dir.iterdir())

    names: List[str] = []
    for src in files:
        ext = src.suffix.lower()
        for _ in range(1000):
            name = f"{prefix}_{_random_suffix(rng)}{ext}"
            if name not in used:
                break
        else:
            raise RuntimeError("Could not generate a unique filename after 1000 attempts")
        used.add(name)
        names.append(name)
    return names


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


def _files_and_names(
    source_dir: Path,
    prefix: str,
    masks: List[str],
    recursive: bool,
    seed: Optional[int],
) -> Tuple[List[Path], List[str], Path]:
    dest_dir = source_dir / prefix
    files = collect_files(source_dir, masks, recursive)
    # Skip files already inside dest_dir to avoid self-copy/move loops
    files = [f for f in files if not _is_inside(f, dest_dir)]
    rng = make_rng(seed)
    names = generate_batch_names(files, prefix, dest_dir, rng)
    return files, names, dest_dir


def preview_rename(
    source_dir: Path,
    prefix: str,
    masks: List[str],
    recursive: bool,
    seed: Optional[int] = None,
) -> List[Tuple[Path, str]]:
    """Return (source_path, new_name) pairs without touching the filesystem."""
    files, names, _dest_dir = _files_and_names(source_dir, prefix, masks, recursive, seed)
    return list(zip(files, names))


def copy_and_rename(
    source_dir: Path,
    prefix: str,
    masks: List[str],
    recursive: bool,
    mode: str = "copy",
    seed: Optional[int] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[RenameResult]:
    """
    Copy or move files from source_dir into source_dir/{prefix}/ with
    randomised names. Returns one RenameResult per file found.
    """
    files, names, dest_dir = _files_and_names(source_dir, prefix, masks, recursive, seed)
    dest_dir.mkdir(exist_ok=True)

    results: List[RenameResult] = []
    total = len(files)

    for i, (src, name) in enumerate(zip(files, names)):
        if cancel_check and cancel_check():
            break

        if progress_cb:
            progress_cb(i, total, src.name)

        try:
            dst = dest_dir / name
            if mode == "move":
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(src, dst)
            results.append(RenameResult(source=src, destination=dst, success=True))
        except Exception as exc:
            results.append(RenameResult(source=src, destination=None, success=False, error=str(exc)))

    if progress_cb:
        progress_cb(total, total, "")

    return results
