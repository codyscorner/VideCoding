"""Background folder scanning.

Reading tags off a slow drive can take tens of seconds for a few hundred files,
so the scan runs in a worker thread and streams tracks to the UI in batches.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from core.library import Track, iter_paths


class ScanWorker(QObject):
    """Runs in a QThread; emits tracks in batches, then finishes.

    Accepts one or more sources (folders and/or individual files).

    Signals:
        batch(list[Track]) — a chunk of newly found tracks
        finished(int)      — scan complete; arg is total tracks emitted
    """

    batch = pyqtSignal(list)
    finished = pyqtSignal(int)

    def __init__(self, sources, recursive: bool, batch_size: int = 25):
        super().__init__()
        # Accept a single folder path or a list of files/folders.
        self._sources = [sources] if isinstance(sources, str) else list(sources)
        self._recursive = recursive
        self._batch_size = batch_size
        self._stop = False

    def stop(self) -> None:
        """Request the scan to halt at the next file boundary."""
        self._stop = True

    def run(self) -> None:
        buffer: list[Track] = []
        total = 0
        for track in iter_paths(self._sources, self._recursive):
            if self._stop:
                break
            buffer.append(track)
            total += 1
            if len(buffer) >= self._batch_size:
                self.batch.emit(buffer)
                buffer = []
        if buffer and not self._stop:
            self.batch.emit(buffer)
        if not self._stop:  # a cancelled scan stays silent
            self.finished.emit(total)
