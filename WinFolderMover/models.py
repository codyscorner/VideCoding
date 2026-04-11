# models.py — shared data contract between the worker thread and the GUI.
# No Qt or OS imports here; this module is intentionally dependency-free.

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    """Tracks the outcome of a single file-move operation.

    Populated by MoveWorker and consumed read-only by MainWindow for
    display and CSV export.
    """

    source_path: str          # Absolute path before the move
    dest_path: str            # Absolute path after the move (intended)
    file_size_bytes: int      # Raw byte count (0 if stat failed)
    file_size_human: str      # Human-readable string, e.g. "1.23 MB"
    time_taken_ms: float      # Wall-clock duration of the move call
    status: str               # "Success" | "Failed" | "Skipped"
    error_detail: Optional[str] = None   # Exception message on failure

    # ------------------------------------------------------------------
    # CSV helpers
    # ------------------------------------------------------------------

    @staticmethod
    def csv_headers() -> list[str]:
        """Column headers for the exported CSV file."""
        return [
            "Source Path",
            "Destination Path",
            "Size (Bytes)",
            "Size (Human)",
            "Time (ms)",
            "Status",
            "Error Detail",
        ]

    def to_csv_row(self) -> list[str]:
        """Ordered values matching csv_headers()."""
        return [
            self.source_path,
            self.dest_path,
            str(self.file_size_bytes),
            self.file_size_human,
            f"{self.time_taken_ms:.1f}",
            self.status,
            self.error_detail or "",
        ]
