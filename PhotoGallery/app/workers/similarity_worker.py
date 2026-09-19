import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.similarity import compute_fingerprint
from app.similarity_cache import SimilarityCache

NUM_WORKERS = max(2, int((os.cpu_count() or 4) * 0.75))
COMMIT_EVERY = 25


class SimilarityIndexWorker(QThread):
    """Background indexer: computes and caches fingerprints for any image
    in the given list that isn't already cached (or whose file changed).
    Safe to run repeatedly — already-indexed files are skipped instantly."""

    progress = pyqtSignal(int, int)   # done, total (of the work actually needed)
    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, paths: List[str], cache: SimilarityCache, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._cache = cache
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            todo = []
            for path in self._paths:
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if self._cache.get(path, st.st_mtime, st.st_size) is None:
                    todo.append((path, st.st_mtime, st.st_size))

            total = len(todo)
            if total == 0:
                self.finished_ok.emit()
                return
            self.progress.emit(0, total)

            done = 0
            with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
                futures = {
                    executor.submit(compute_fingerprint, path): (path, mtime, size)
                    for path, mtime, size in todo
                }
                for future in as_completed(futures):
                    if self._cancelled:
                        for f in futures:
                            f.cancel()
                        break
                    path, mtime, size = futures[future]
                    try:
                        fingerprint = future.result()
                        self._cache.put(path, mtime, size, fingerprint)
                    except Exception:
                        pass
                    done += 1
                    if done % COMMIT_EVERY == 0:
                        self._cache.commit()
                    self.progress.emit(done, total)
            self._cache.commit()
            if not self._cancelled:
                self.finished_ok.emit()
        except Exception as e:
            self.error.emit(str(e))
