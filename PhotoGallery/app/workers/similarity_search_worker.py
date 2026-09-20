from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from app.similarity import Fingerprint, face_distance, visual_similarity_score
from app.similarity_cache import SimilarityCache
from app.workers.thumbnail_worker import is_video


class SimilaritySearchWorker(QThread):
    """Ranks every already-indexed image in the folder against a reference
    fingerprint. Runs off the UI thread because doing this inline froze the
    window on large (10k+) libraries."""

    finished_ok = pyqtSignal(list, dict, bool, int, int)  # order, scores, used_faces, indexed, total
    error = pyqtSignal(str)

    def __init__(
        self,
        all_paths: List[str],
        cache: SimilarityCache,
        ref_fingerprint: Fingerprint,
        face_tolerance: float,
        parent=None,
    ):
        super().__init__(parent)
        self._all_paths = all_paths
        self._cache = cache
        self._ref_phash, self._ref_hist, self._ref_faces = ref_fingerprint
        self._face_tolerance = face_tolerance
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            still_paths = [p for p in self._all_paths if not is_video(p)]
            fingerprints = self._cache.get_many(still_paths)
            indexed = len(fingerprints)
            total_all = len(still_paths)

            if self._cancelled:
                return

            order: List[str] = []
            scores: dict = {}
            used_faces = False

            if self._ref_faces:
                face_matches = []
                for path, (phash, hist, faces) in fingerprints.items():
                    if self._cancelled:
                        return
                    if not faces:
                        continue
                    best = min(
                        face_distance(rf, cf) for rf in self._ref_faces for cf in faces
                    )
                    if best <= self._face_tolerance:
                        face_matches.append((path, best))
                if face_matches:
                    face_matches.sort(key=lambda pair: pair[1])
                    order = [p for p, _ in face_matches]
                    scores = {
                        p: max(0.0, 1.0 - d / self._face_tolerance) for p, d in face_matches
                    }
                    used_faces = True

            if not used_faces:
                visual = [
                    (path, visual_similarity_score(self._ref_phash, self._ref_hist, phash, hist))
                    for path, (phash, hist, faces) in fingerprints.items()
                ]
                if self._cancelled:
                    return
                visual.sort(key=lambda pair: pair[1], reverse=True)
                order = [p for p, _ in visual]
                scores = dict(visual)

            if not self._cancelled:
                self.finished_ok.emit(order, scores, used_faces, indexed, total_all)
        except Exception as e:
            self.error.emit(str(e))
