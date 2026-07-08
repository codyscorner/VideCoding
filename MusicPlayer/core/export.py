"""Export a playlist's actual audio files to a destination folder (e.g. a USB
drive), optionally writing an .m3u alongside.

Deliberately format-agnostic: it just copies files (flat or preserving their
folder structure) plus an optional standard .m3u — no car-specific layouts.
"""

from __future__ import annotations

import os
import shutil

from PyQt6.QtCore import QObject, pyqtSignal

from core.library import Track


def _common_base(paths: list[str]) -> str | None:
    dirs = [os.path.dirname(p) for p in paths]
    if not dirs:
        return None
    if len(dirs) == 1:
        return dirs[0]
    try:
        return os.path.commonpath(dirs)
    except ValueError:
        return None  # e.g. different drives — no shared base


def plan_targets(
    tracks: list[Track], dest: str, preserve: bool
) -> list[tuple[str, str]]:
    """Map each track to its (source, target) path under ``dest``.

    preserve=True keeps each file's path relative to the tracks' common base
    folder; preserve=False copies everything flat, disambiguating same-named
    files with " (2)", " (3)", … so none are lost.
    """
    dest = os.path.abspath(dest)
    base = _common_base([t.path for t in tracks]) if preserve else None
    used: set[str] = set()
    targets: list[tuple[str, str]] = []

    for t in tracks:
        src = t.path
        if preserve and base:
            try:
                rel = os.path.relpath(src, base)
            except ValueError:
                rel = os.path.basename(src)
            target = os.path.join(dest, rel)
        else:
            target = os.path.join(dest, os.path.basename(src))
            if target.lower() in used:
                stem, ext = os.path.splitext(os.path.basename(src))
                n = 2
                while os.path.join(dest, f"{stem} ({n}){ext}").lower() in used:
                    n += 1
                target = os.path.join(dest, f"{stem} ({n}){ext}")
        used.add(target.lower())
        targets.append((src, target))
    return targets


def write_m3u(m3u_path: str, tracks: list[Track], targets: list[tuple[str, str]]) -> None:
    """Write a UTF-8 #EXTM3U file with paths relative to the .m3u's folder."""
    dest_dir = os.path.dirname(m3u_path)
    lines = ["#EXTM3U"]
    for track, (_src, target) in zip(tracks, targets):
        rel = os.path.relpath(target, dest_dir).replace(os.sep, "/")
        artist = track.artist.strip()
        title = track.display_title
        disp = f"{artist} - {title}" if artist else title
        lines.append(f"#EXTINF:{int(track.duration_secs)},{disp}")
        lines.append(rel)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


class ExportWorker(QObject):
    """Copies planned files on a worker thread, reporting progress."""

    progress = pyqtSignal(int, int, str)   # done, total, current name
    finished = pyqtSignal(int, int, int)   # copied, skipped, errors

    def __init__(
        self,
        targets: list[tuple[str, str]],
        overwrite: bool,
        m3u_path: str | None = None,
        m3u_tracks: list[Track] | None = None,
    ):
        super().__init__()
        self._targets = targets
        self._overwrite = overwrite
        self._m3u_path = m3u_path
        self._m3u_tracks = m3u_tracks
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        copied = skipped = errors = 0
        total = len(self._targets)
        for i, (src, dst) in enumerate(self._targets):
            if self._cancel:
                break
            self.progress.emit(i, total, os.path.basename(dst))
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst) and not self._overwrite:
                    skipped += 1
                else:
                    shutil.copy2(src, dst)
                    copied += 1
            except OSError:
                errors += 1

        if not self._cancel and self._m3u_path and self._m3u_tracks is not None:
            try:
                write_m3u(self._m3u_path, self._m3u_tracks, self._targets)
            except OSError:
                pass

        self.progress.emit(total, total, "")
        self.finished.emit(copied, skipped, errors)
