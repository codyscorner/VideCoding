from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from models import BackupRecord


class BackupWorker(QThread):
    """Runs all backup steps off the GUI thread.

    Each run creates one dated folder inside the destination:

        Destination/
          2026-04-11/
            AI/          <- contents of P:/AI
            Documents/   <- contents of P:/Documents
          2026-04-10/
            ...

    If today's dated folder already exists (backup ran twice today),
    any files that changed since the first run are versioned before
    being overwritten:
        photo.jpg  →  photo_v2026-04-11_091022.jpg

    Retention deletes dated folders older than N days.

    Signals
    -------
    log_signal      (str)   — line of text for the status log
    progress_signal (int)   — 0-100 progress value
    finished_signal (list)  — list[BackupRecord] on completion
    error_signal    (str)   — unrecoverable error message
    """

    log_signal      = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)
    error_signal    = pyqtSignal(str)

    def __init__(
        self,
        sources: list[str],
        destination: str,
        retention_days: int,
        threads: int,
        log_dir: Path,
        versioned_files: bool = True,
    ) -> None:
        super().__init__()
        self._sources         = sources
        self._destination     = destination
        self._retention_days  = retention_days
        self._threads         = threads
        self._log_dir         = log_dir
        self._versioned_files = versioned_files
        self._cancelled       = False

    def cancel(self) -> None:
        self._cancelled = True

    # ------------------------------------------------------------------
    # Main thread entry
    # ------------------------------------------------------------------

    def run(self) -> None:
        records: list[BackupRecord] = []
        date_stamp = datetime.now().strftime("%Y-%m-%d")
        today_folder = os.path.join(self._destination, date_stamp)

        # Total steps: one copy per source + retention + verify
        total_steps = len(self._sources) + 2
        step = 0

        try:
            for source in self._sources:
                if self._cancelled:
                    break

                source_name = Path(source).name
                dest_sub    = os.path.join(today_folder, source_name)

                # ── Same-day versioning pre-pass ───────────────────────
                # Only runs if today's folder already exists from an
                # earlier run today.
                if self._versioned_files and os.path.exists(dest_sub):
                    self.log_signal.emit(
                        f"\n  Today's folder exists — checking for changed files in [{source_name}]…"
                    )
                    versioned = self._version_existing_files(source, dest_sub)
                    if versioned:
                        self.log_signal.emit(f"  ✓ {versioned} file(s) versioned")
                    else:
                        self.log_signal.emit(f"  ✓ No changed files")

                # ── Backup into dated folder ───────────────────────────
                step += 1
                self._emit_progress(step, total_steps)
                self.log_signal.emit(
                    f"\n[{step}/{total_steps}] Backing up: {source}"
                    f"\n             → {dest_sub}"
                )

                os.makedirs(dest_sub, exist_ok=True)
                record = self._run_robocopy(source, dest_sub, label=source_name)
                records.append(record)

                if self._cancelled:
                    break

            if not self._cancelled:
                # ── Retention policy ───────────────────────────────────
                step += 1
                self._emit_progress(step, total_steps)
                self.log_signal.emit(
                    f"\n[{step}/{total_steps}] Applying retention policy ({self._retention_days} days)…"
                )
                self._apply_retention()

                # ── Verification ───────────────────────────────────────
                step += 1
                self._emit_progress(step, total_steps)
                self.log_signal.emit(f"\n[{step}/{total_steps}] Verifying today's backup…")
                self._verify(today_folder)

            self.progress_signal.emit(100)
            status = "CANCELLED" if self._cancelled else "COMPLETE"
            self.log_signal.emit(f"\n{'=' * 44}")
            self.log_signal.emit(f"BACKUP {status}")
            self.log_signal.emit(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_signal.emit(f"{'=' * 44}")

        except Exception as exc:  # noqa: BLE001
            self.error_signal.emit(str(exc))
            return

        self.finished_signal.emit(records)

    # ------------------------------------------------------------------
    # Same-day versioning pre-pass
    # ------------------------------------------------------------------

    def _version_existing_files(self, source: str, dest: str) -> int:
        """Rename destination files that differ from source.

        Called only when today's dated folder already exists (i.e. this
        is the second or later backup run of the day).  Files with the
        same size and mtime are left untouched; changed files are renamed
        to include their current timestamp before robocopy overwrites them.

        Returns the count of files versioned.
        """
        versioned = 0

        for root, _dirs, files in os.walk(source):
            rel_dir = os.path.relpath(root, source)
            for fname in files:
                if self._cancelled:
                    return versioned

                dst_file = (
                    os.path.join(dest, fname)
                    if rel_dir == "."
                    else os.path.join(dest, rel_dir, fname)
                )

                if not os.path.exists(dst_file):
                    continue

                src_file = os.path.join(root, fname)

                try:
                    same_size  = os.path.getsize(src_file) == os.path.getsize(dst_file)
                    same_mtime = abs(os.path.getmtime(src_file) - os.path.getmtime(dst_file)) <= 2.0
                except OSError:
                    continue

                if same_size and same_mtime:
                    continue

                # Rename using the DESTINATION file's current mtime
                name, ext = os.path.splitext(fname)
                dt_str = datetime.fromtimestamp(
                    os.path.getmtime(dst_file)
                ).strftime("%Y-%m-%d_%H%M%S")
                versioned_name = f"{name}_v{dt_str}{ext}"
                versioned_path = os.path.join(os.path.dirname(dst_file), versioned_name)

                try:
                    os.rename(dst_file, versioned_path)
                    self.log_signal.emit(f"    [v] {fname}  ->  {versioned_name}")
                    versioned += 1
                except OSError as exc:
                    self.log_signal.emit(f"    ⚠ Could not version {fname}: {exc}")

        return versioned

    # ------------------------------------------------------------------
    # Robocopy helper
    # ------------------------------------------------------------------

    def _run_robocopy(self, source: str, dest: str, label: str) -> BackupRecord:
        args = [
            "robocopy", source, dest,
            "/E", "/FFT",
            f"/MT:{self._threads}",
            "/W:5", "/R:3", "/NDL", "/TEE", "/BYTES",
        ]

        self.log_signal.emit(f"  cmd: {' '.join(args)}")
        start     = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result    = subprocess.run(args, capture_output=False)
        elapsed   = time.time() - start

        h, rem = divmod(int(elapsed), 3600)
        m, s   = divmod(rem, 60)
        duration = f"{h:02d}:{m:02d}:{s:02d}"

        ok     = result.returncode <= 7
        status = "OK" if ok else "FAILED"
        error  = "" if ok else f"robocopy exit code {result.returncode}"

        if ok:
            self.log_signal.emit(f"  ✓ [{label}] completed in {duration}")
        else:
            self.log_signal.emit(f"  ✗ [{label}] FAILED (exit {result.returncode})")

        return BackupRecord(
            source=source,
            destination=dest,
            timestamp=timestamp,
            duration=duration,
            files_copied=0,
            total_size_gb=0.0,
            status=status,
            error=error,
        )

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------

    def _apply_retention(self) -> None:
        """Delete dated folders in destination older than retention_days.

        Folder names are expected to be in YYYY-MM-DD format.  Folders
        that don't match that pattern are left untouched.
        """
        if not os.path.exists(self._destination):
            return

        cutoff  = datetime.now() - timedelta(days=self._retention_days)
        deleted = 0

        for item in os.listdir(self._destination):
            item_path = os.path.join(self._destination, item)
            if not os.path.isdir(item_path):
                continue
            try:
                folder_date = datetime.strptime(item, "%Y-%m-%d")
            except ValueError:
                continue  # not a dated folder — skip
            if folder_date < cutoff:
                self.log_signal.emit(f"  Deleting old backup: {item}")
                shutil.rmtree(item_path)
                deleted += 1

        msg = f"  ✓ {deleted} old backup(s) deleted" if deleted else "  ✓ No old backups to delete"
        self.log_signal.emit(msg)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify(self, path: str) -> None:
        file_count  = 0
        total_bytes = 0
        for root, _dirs, files in os.walk(path):
            file_count += len(files)
            for f in files:
                try:
                    total_bytes += os.path.getsize(os.path.join(root, f))
                except (OSError, FileNotFoundError):
                    pass
        size_gb = round(total_bytes / (1024 ** 3), 2)
        self.log_signal.emit(f"  ✓ Files in today's backup: {file_count:,}")
        self.log_signal.emit(f"  ✓ Total size: {size_gb} GB")

    # ------------------------------------------------------------------
    # Progress helper
    # ------------------------------------------------------------------

    def _emit_progress(self, step: int, total: int) -> None:
        self.progress_signal.emit(int((step / total) * 90))
