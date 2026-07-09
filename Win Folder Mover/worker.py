# worker.py — MoveWorker(QThread)
#
# All file-system logic lives here.  This class must never import or
# reference any Qt widget.  It communicates exclusively via pyqtSignals.
#
# pip install PyQt6

from __future__ import annotations

import os
import shutil
import stat
import time
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from models import FileRecord


# ---------------------------------------------------------------------------
# Utility helpers (module-level so they are unit-testable in isolation)
# ---------------------------------------------------------------------------

def _long_path(p: str) -> str:
    """Prepend the Windows extended-length path prefix to bypass MAX_PATH.

    Only applied when the path actually exceeds 260 characters, and only
    for local drive paths — mapped drives and UNC paths are returned as-is
    because \\\\?\\ does not resolve correctly against them.
    """
    p = os.path.abspath(p)
    if len(p) <= 260:
        return p                     # short enough — no prefix needed
    if p.startswith("\\\\"):         # UNC or mapped drive — leave as-is
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


def _clear_readonly(path: str) -> None:
    """Remove the read-only attribute from *path* if it is set.

    Old files (especially scanned photos) often carry the read-only flag.
    Clearing it before a copy/move prevents [Errno 13] Permission denied
    when overwriting an existing destination file.
    """
    try:
        mode = os.stat(path).st_mode
        if not (mode & stat.S_IWRITE):
            os.chmod(path, mode | stat.S_IWRITE)
    except OSError:
        pass


def _copy_file(src: str, dst: str) -> None:
    """Copy *src* to *dst* (fallback when a move is denied).

    Used when a PermissionError prevents the source file from being
    deleted — the data is still safely duplicated at the destination.
    """
    dst_lp = _long_path(dst)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    if os.path.exists(dst_lp):
        _clear_readonly(dst_lp)
    shutil.copy2(_long_path(src), dst_lp)


def _same_drive(a: str, b: str) -> bool:
    """True if *a* and *b* resolve to the same drive letter/UNC root."""
    return (
        os.path.splitdrive(os.path.abspath(a))[0].lower()
        == os.path.splitdrive(os.path.abspath(b))[0].lower()
    )


def _move_file(src: str, dst: str, verify: bool = False) -> None:
    """Move *src* to *dst*.

    Same-drive moves use ``shutil.move`` (which resolves to an atomic
    ``os.rename`` — either the whole file moves or nothing does, so no
    verification is needed there). Cross-drive moves are copy + delete;
    when *verify* is set, the destination's size is compared against the
    source's before the source is removed, so a truncated/corrupt copy
    leaves the source file in place instead of silently losing data.

    Read-only attributes on the source and any existing destination file
    are cleared before the move so that old/archived files (e.g. scanned
    photos with the read-only flag) transfer without permission errors.
    """
    dst_lp = _long_path(dst)
    src_lp = _long_path(src)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    # Clear read-only on source (needed for delete after cross-drive copy)
    _clear_readonly(src_lp)
    # Clear read-only on destination if it already exists
    if os.path.exists(dst_lp):
        _clear_readonly(dst_lp)

    if _same_drive(src, dst):
        shutil.move(src_lp, dst_lp)
        return

    shutil.copy2(src_lp, dst_lp)
    if verify:
        src_size = _safe_size(src_lp)
        dst_size = _safe_size(dst_lp)
        if src_size != dst_size:
            raise OSError(
                f"Verification failed: size mismatch ({src_size} vs {dst_size} bytes) "
                "— source left in place"
            )
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

    def __init__(
        self,
        source: str,
        dest: str,
        dry_run: bool = False,
        verify: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source  = source
        self.dest    = dest
        self.dry_run = dry_run
        self.verify  = verify
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

    def _retry_failed(self, records: list[FileRecord]) -> list[FileRecord]:
        """Second pass over files that failed on the first try.

        A file locked by another process (e.g. still being written, or
        held open in another app) often frees up within a second or two —
        this retries each failure once more before giving up for good.
        """
        retryable = [r for r in records if r.status == "Failed"]
        if not retryable:
            return records

        self.log_signal.emit(f"\nRetrying {len(retryable)} locked/failed file(s)…")
        for i, record in enumerate(retryable, start=1):
            if self._cancel:
                break

            rel = os.path.relpath(record.source_path, self.source)
            self.log_signal.emit(f"  Retry [{i}/{len(retryable)}]  {rel}")

            if not os.path.exists(_long_path(record.source_path)):
                self.log_signal.emit("    ✗ Source no longer exists — skipping retry")
                continue

            time.sleep(0.5)  # give whatever was locking the file a moment to release it
            try:
                _move_file(record.source_path, record.dest_path, verify=self.verify)
                record.status = "Success"
                record.error_detail = f"Recovered on retry (was: {record.error_detail})"
                self.log_signal.emit("    ✓ Recovered on retry")
            except Exception as exc:
                record.error_detail = f"{record.error_detail} | Retry also failed: {exc}"
                self.log_signal.emit(f"    ✗ Retry failed — {exc}")

        return records

    def _do_move(self) -> list[FileRecord]:
        """Core logic.  Returns the (possibly partial) list of records."""
        records: list[FileRecord] = []

        # ---- Phase 1: scan -----------------------------------------------
        mode_label = "DRY RUN — no files will be moved" if self.dry_run else "Move"
        self.log_signal.emit(f"Mode:        {mode_label}")
        self.log_signal.emit(f"Source:      {self.source}")
        self.log_signal.emit(f"Destination: {self.dest}")
        self.log_signal.emit("Scanning source directory…")

        all_files: list[str] = []
        for root, _dirs, files in os.walk(self.source):
            for fname in files:
                all_files.append(os.path.join(root, fname))

        total = len(all_files)
        if total == 0:
            self.log_signal.emit("No files found in the source directory.")
            return records

        action_word = "Previewing" if self.dry_run else "Starting move of"
        self.log_signal.emit(f"Found {total:,} file(s). {action_word} {total:,} file(s)…")
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

            if self.dry_run:
                # Preview only — report what would happen without touching files.
                if os.path.exists(dst_path) and _safe_size(dst_path) == size_bytes:
                    status       = "Skipped"
                    error_detail = "Dry run — duplicate at destination (same size)"
                    self.log_signal.emit(f"  [DRY] Would skip — already exists at destination")
                else:
                    status       = "Would Move"
                    error_detail = None
                    self.log_signal.emit(f"  [DRY] Would move  →  {dst_path}")
            else:
                # ── Duplicate check ───────────────────────────────────────
                # If the destination already exists and is the same size,
                # skip the move entirely — source is left untouched.
                if os.path.exists(dst_path) and _safe_size(dst_path) == size_bytes:
                    status       = "Skipped"
                    error_detail = "Duplicate — same size at destination, source left intact"
                    self.log_signal.emit(f"  ↷ Skipped — already exists at destination")
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
                    self.progress_signal.emit(round(idx / total * 100))
                    continue

                try:
                    _move_file(src_path, dst_path, verify=self.verify)

                except PermissionError as exc:
                    self.log_signal.emit(
                        f"  ⚠ Permission denied — attempting copy fallback…"
                    )
                    try:
                        _copy_file(src_path, dst_path)
                        status       = "Copied"
                        error_detail = f"Moved denied, copied only — {exc}"
                        self.log_signal.emit(
                            f"  ✓ Copied (source not deleted)"
                        )
                    except Exception as copy_exc:
                        status       = "Failed"
                        error_detail = f"PermissionError: {exc} | Copy also failed: {copy_exc}"
                        self.log_signal.emit(
                            f"  ✗ Copy fallback also failed — {copy_exc}"
                        )

                except FileNotFoundError as exc:
                    status       = "Failed"
                    error_detail = f"FileNotFoundError: {exc}"
                    self.log_signal.emit(
                        f"  ✗ File not found — {exc}"
                    )

                except OSError as exc:
                    status       = "Failed"
                    detail       = exc.strerror or str(exc)
                    error_detail = f"OSError [{exc.errno}]: {detail}" if exc.errno else str(exc)
                    self.log_signal.emit(f"  ✗ OS error — {detail}")

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

        # ---- Phase 3: retry locked/failed files ---------------------------
        if not self.dry_run:
            records = self._retry_failed(records)

        # ---- Summary line -----------------------------------------------
        if self.dry_run:
            would_move = sum(1 for r in records if r.status == "Would Move")
            skipped    = sum(1 for r in records if r.status == "Skipped")
            self.log_signal.emit(
                f"\n── Dry Run Complete ──\n"
                f"  Would move:  {would_move:,}\n"
                f"  Would skip:  {skipped:,}\n"
                f"  Total:       {len(records):,}\n"
                f"\nNo files were moved. Uncheck Dry Run and click Start Move to proceed."
            )
        else:
            moved   = sum(1 for r in records if r.status == "Success")
            copied  = sum(1 for r in records if r.status == "Copied")
            skipped = sum(1 for r in records if r.status == "Skipped")
            failed  = sum(1 for r in records if r.status == "Failed")
            self.log_signal.emit(
                f"\n── Finished ──\n"
                f"  Moved:   {moved:,}\n"
                f"  Copied:  {copied:,}\n"
                f"  Skipped: {skipped:,}\n"
                f"  Failed:  {failed:,}\n"
                f"  Total:   {len(records):,}"
            )

        return records
