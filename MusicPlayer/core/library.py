"""Folder scanning for Music Player.

Phase 1: walk a directory (optionally recursing into subfolders) and collect
audio files with the basic attributes we can read straight from the filesystem —
name, size, format. Richer tag metadata (title/artist/album/duration) arrives in
Phase 3.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from tinytag import TinyTag
except ImportError:  # metadata is optional; scanning still works without it
    TinyTag = None  # type: ignore[assignment]

# Formats we scan for (Phase 1 decision).
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}

# Files smaller than this are treated as junk (empty/corrupt) and skipped —
# no real playable track is this tiny.
MIN_TRACK_SIZE_BYTES = 10 * 1024  # 10 KB


@dataclass
class Track:
    """One audio file discovered on disk.

    Phase 1 fills the filesystem-derived fields. Tag fields default to empty and
    get populated in Phase 3.
    """

    path: str
    name: str          # file name without extension
    size_bytes: int
    ext: str           # lowercase, without the dot (e.g. "mp3")

    # Placeholders for later phases.
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_secs: float = 0.0

    @classmethod
    def from_path(cls, path: Path) -> "Track":
        stat = path.stat()
        return cls(
            path=str(path),
            name=path.stem,
            size_bytes=stat.st_size,
            ext=path.suffix.lower().lstrip("."),
        )

    @property
    def display_title(self) -> str:
        """Tag title if present, otherwise the file name."""
        return self.title or self.name


def read_tags(track: Track) -> None:
    """Populate a track's title/artist/album/duration from its file tags.

    Best-effort: leaves defaults in place if tinytag is missing or the file has
    no readable tags.
    """
    if TinyTag is None:
        return
    try:
        tag = TinyTag.get(track.path)
    except Exception:
        return
    track.title = (tag.title or "").strip()
    track.artist = (tag.artist or "").strip()
    track.album = (tag.album or "").strip()
    track.duration_secs = float(tag.duration or 0.0)


def read_album_art(path: str) -> bytes | None:
    """Return embedded cover-art image bytes for a file, or None."""
    if TinyTag is None:
        return None
    try:
        tag = TinyTag.get(path, image=True)
        image = tag.get_image()
    except Exception:
        return None
    return image or None


def format_duration(seconds: float) -> str:
    """Seconds -> "m:ss" / "h:mm:ss"; empty string when unknown (0)."""
    total = int(seconds)
    if total <= 0:
        return ""
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def iter_tracks(folder: str | os.PathLike, recursive: bool = True):
    """Yield audio ``Track``s found in ``folder``, tags included, one at a time.

    Yielding lets a background worker stream results to the UI instead of
    blocking until the whole (possibly slow) folder is read. Files are walked in
    sorted-by-path order for a stable initial order.
    """
    root = Path(folder)
    if not root.is_dir():
        return

    walker = root.rglob("*") if recursive else root.glob("*")
    try:
        entries = sorted(walker, key=lambda p: str(p).lower())
    except OSError:
        return

    for entry in entries:
        try:
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
                track = Track.from_path(entry)
                if track.size_bytes < MIN_TRACK_SIZE_BYTES:
                    continue  # skip empty/corrupt junk files
                read_tags(track)
                yield track
        except OSError:
            # Skip unreadable / vanished files rather than aborting the scan.
            continue


def _read_audio_file(path: Path) -> "Track | None":
    """Build a tagged Track from a single audio file, or None if not usable."""
    try:
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            return None
        track = Track.from_path(path)
        if track.size_bytes < MIN_TRACK_SIZE_BYTES:
            return None
        read_tags(track)
        return track
    except OSError:
        return None


def iter_paths(sources, recursive: bool = True):
    """Yield tracks for a mix of files and folders (e.g. an Explorer drop).

    Folders are walked (respecting ``recursive``); individual files are added
    directly. Duplicate paths across the sources are yielded only once.
    """
    seen: set[str] = set()
    for src in sources:
        p = Path(src)
        if p.is_dir():
            for track in iter_tracks(p, recursive):
                if track.path not in seen:
                    seen.add(track.path)
                    yield track
        else:
            track = _read_audio_file(p)
            if track and track.path not in seen:
                seen.add(track.path)
                yield track


def scan_folder(folder: str | os.PathLike, recursive: bool = True) -> list[Track]:
    """Return all audio tracks in ``folder`` as a list (synchronous)."""
    return list(iter_tracks(folder, recursive))


def human_size(size_bytes: int) -> str:
    """Format a byte count as a compact human-readable string (e.g. 8.1 MB)."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
