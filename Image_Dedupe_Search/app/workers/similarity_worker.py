"""Worker thread for computing image similarity"""

from PySide6.QtCore import QThread, Signal
from typing import Dict, List, Optional
import numpy as np

from app.core.similarity import SimilarityEngine, DuplicateGroup


class SimilarityWorker(QThread):
    """Worker thread for computing image similarity"""

    # Signals
    progress = Signal(int, int)  # current, total comparisons
    finished = Signal(list)  # List[DuplicateGroup]
    error = Signal(str)  # Error message
    status = Signal(str)  # Status message

    def __init__(
        self,
        embeddings: Dict[str, np.ndarray],
        image_metadata: Optional[Dict[str, dict]] = None,
        threshold: float = 0.92,
        parent=None
    ):
        """
        Initialize similarity worker

        Args:
            embeddings: Dict mapping image path to embedding vector
            image_metadata: Optional dict mapping path to metadata
            threshold: Minimum similarity to consider as duplicate (0-1)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.embeddings = embeddings
        self.image_metadata = image_metadata or {}
        self.threshold = threshold
        self._is_cancelled = False

    def run(self) -> None:
        """
        Compute similarity and find duplicate groups

        1. Compute pairwise cosine similarity
        2. Filter by threshold
        3. Group duplicates
        4. Emit finished with duplicate groups
        """
        try:
            n = len(self.embeddings)
            if n < 2:
                self.finished.emit([])
                return

            self.status.emit(f"Computing similarity for {n} images...")

            # Create similarity engine
            engine = SimilarityEngine(threshold=self.threshold)

            # Define progress callback
            def on_progress(current: int, total: int):
                if self._is_cancelled:
                    return
                self.progress.emit(current, total)

            # Compute pairwise similarities
            self.status.emit("Computing pairwise similarities...")
            similarities = engine.compute_pairwise_similarity(
                self.embeddings,
                progress_callback=on_progress
            )

            if self._is_cancelled:
                return

            # Find duplicate groups
            self.status.emit(f"Found {len(similarities)} similar pairs, grouping...")
            groups = engine.find_duplicate_groups(
                similarities,
                self.image_metadata
            )

            if self._is_cancelled:
                return

            self.status.emit(f"Found {len(groups)} duplicate groups")
            self.finished.emit(groups)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Request cancellation"""
        self._is_cancelled = True
