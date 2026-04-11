# worker.py — MoveWorker(QThread)
#
# All file-system logic lives here.  This class must never import or
# reference any Qt widget.  It communicates exclusively via pyqtSignals.
#
# pip install PyQt6

from __future__ import annotations

import os
import shutil
import time
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from models import FileRecord


# ---------------------------------------------------------------------------
# Utility helpers (module-level so they are unit-testable in isolation)
# ---------------------------------------------------------------------------

def _long_path(p: str) -> str:
    """Prepend the Windows extended-length path prefix to bypass MAX_PATH.

    The NT kernel supports paths up to 32 767 characters when the caller
    uses the ``\\\\?\\`` prefix.  Without it, any path longer than 260
    characters raises FileNotFoundError or similar OS errors.

    UNC paths (``\\\\server\\share\\...``) are returned unchanged because
    they require a different prefix (``\\\\?\\UNC\\...``) that is beyond
    the scope of this tool.
    """
    p = os.path.abspath(p)          # guarantee absolute + normalised
    if p.startswith("\\\\"):        # UNC — leave as-is
        return p
    if not p.startswith("\\\\?\\"):
        p = "\\\\?\\" + p
    return p


def _format_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.2f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.2f} MB"
    if size_bytes >= 1_024:
        return f"{size_bytes / 1_024:.2f} KB"
    return f"{size_bytes} B"


def _safe_size(path: str) -> int:
    """Return file size in bytes, or 0 if stat fails (e.g. permission)."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _move_file(src: str, dst: str) -> None:
    """Move *src* to *dst*, applying long-path prefixes on both ends.

    Strategy:
    - Same drive  → ``os.rename`` (atomic, instant, no extra disk I/O)
    - Cross drive → ``shutil.copy2`` then ``os.remove``
                    (shutil.move would work too, but being explicit about
                     the fallback path makes error attribution clearer)

    The destination directory is created (including any intermediate
    parents) before the move is attempted.
    """
    src_lp = _long_path(src)
    dst_lp = _long_path(dst)

    dst_dir = os.path.dirname(dst_lp)
    os.makedirs(dst_dir, exist_ok=True)

    src_drive = os.path.splitdrive(src)[0].lower()
    dst_drive = os.path.splitdrive(dst)[0].lower()

    if src_drive == dst_drive:
        # Same volume: rename is O(1) and never leaves a partial copy.
        os.rename(src_lp, dst_lp)
    else:
        # Cross-volume: full byte copy then source deletion.
        shutil.copy2(src_lp, dst_lp)
        os.remove(src_lp)


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class MoveWorker(QThread):
    """Recursively moves all files from *source* to *dest* on a background
    thread, emitting fine-grained signals so the GUI can stay fully
    responsive throughout the operation.

    Signal contract
    ---------------
    log_signal(str)       — human-readable status line for the log pane
    progress_signal(int)  — 0–100 percentage for the progress bar
    finished_signal(list) — list[FileRecord] for the whole session
                            (always emitted, even after cancellation)
    error_signal(str)     — critical / unrecoverable error message
    """

    log_signal      = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)   # list[FileRecord]
    error_signal    = pyqtSignal(str)

    def __init__(self, source: str, dest: str, parent=None) -> None:
        super().__init__(parent)
        self.source = source
        self.dest   = dest
        self._cancel = False            # checked between every file

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request a graceful stop after the current file completes."""
        self._cancel = True

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Called by Qt when the thread starts.  Never call this directly."""
        records: list[FileRecord] = []
        try:
            records = self._do_move()
        except Exception as exc:                         # pragma: no cover
            # Catches any unexpected exception that escaped _do_move so
            # that finished_signal is *always* emitted and the GUI can
            # re-enable its controls.
            self.error_signal.emit(
                f"Unhandled worker error: {type(exc).__name__}: {exc}"
            )
        finally:
            self.finished_signal.emit(records)

    # ------------------------------------------------------------------
    # Internal implementation
    # ------------------------------------------------------------------

    def _do_move(self) -> list[FileRecord]:
        """Core logic.  Returns the (possibly partial) list of records."""
        records: list[FileRecord] = []

        # ---- Phase 1: scan -----------------------------------------------
        self.log_signal.emit("Scanning source directory…")

        all_files: list[str] = []
        for root, _dirs, files in os.walk(self.source):
            for fname in files:
                all_files.append(os.path.join(root, fname))

        total = len(all_files)
        if total == 0:
            self.log_signal.emit("No files found in the source directory.")
            return records

        self.log_signal.emit(f"Found {total:,} file(s). Starting move…")
        self.progress_signal.emit(0)

        # ---- Phase 2: move -----------------------------------------------
        for idx, src_path in enumerate(all_files, start=1):

            # Honour a cancellation request between files.
            if self._cancel:
                self.log_signal.emit(
                    f"\nCancelled by user after {idx - 1:,} file(s)."
                )
                break

            # Preserve the relative directory structure inside dest.
            rel      = os.path.relpath(src_path, self.source)
            dst_path = os.path.join(self.dest, rel)

            # Measure size *before* the move (file still exists on disk).
            size_bytes = _safe_size(_long_path(src_path))
            size_human = _format_size(size_bytes)

            self.log_signal.emit(f"[{idx}/{total}]  {rel}")

            status:       str           = "Success"
            error_detail: Optional[str] = None
            t_start = time.perf_counter()

            try:
                _move_file(src_path, dst_path)

            except PermissionError as exc:
                # File locked by another process, or insufficient privileges.
                status       = "Failed"
                error_detail = f"PermissionError: {exc}"
                self.log_signal.emit(
                    f"  ✗ Permission denied — {exc}"
                )

            except FileNotFoundError as exc:
                # Source vanished mid-run, or an extremely long path slipped
                # through the long-path guard.
                status       = "Failed"
                error_detail = f"FileNotFoundError: {exc}"
                self.log_signal.emit(
                    f"  ✗ File not found — {exc}"
                )

            except OSError as exc:
                # Catch-all for other OS-level failures (disk full, bad
                # sectors, cross-device rename edge cases, …).
                status       = "Failed"
                error_detail = f"OSError [{exc.errno}]: {exc.strerror}"
                self.log_signal.emit(
                    f"  ✗ OS error {exc.errno} — {exc.strerror}"
                )

            elapsed_ms = (time.perf_counter() - t_start) * 1_000

            records.append(FileRecord(
                source_path    = src_path,
                dest_path      = dst_path,
                file_size_bytes= size_bytes,
                file_size_human= size_human,
                time_taken_ms  = elapsed_ms,
                status         = status,
                error_detail   = error_detail,
            ))

            # Update the progress bar (integer 0-100).
            self.progress_signal.emit(round(idx / total * 100))

        # ---- Summary line -----------------------------------------------
        succeeded = sum(1 for r in records if r.status == "Success")
        failed    = sum(1 for r in records if r.status == "Failed")
        self.log_signal.emit(
            f"\n── Finished ──\n"
            f"  Moved:  {succeeded:,}\n"
            f"  Failed: {failed:,}\n"
            f"  Total:  {len(records):,}"
        )

        return records
