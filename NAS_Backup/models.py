from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackupRecord:
    source: str
    destination: str
    timestamp: str
    duration: str
    files_copied: int
    total_size_gb: float
    status: str      # "OK" | "FAILED" | "CANCELLED"
    error: str       # empty string if no error

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "Source",
            "Destination",
            "Timestamp",
            "Duration",
            "Files Copied",
            "Total Size (GB)",
            "Status",
            "Error",
        ]

    def to_csv_row(self) -> list:
        return [
            self.source,
            self.destination,
            self.timestamp,
            self.duration,
            self.files_copied,
            self.total_size_gb,
            self.status,
            self.error,
        ]
