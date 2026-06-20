"""Worker thread for computing image embeddings"""

from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Optional
import numpy as np

from app.core.embeddings import EmbeddingEngine
from app.core.cache import EmbeddingCache


class EmbedWorker(QThread):
    """Worker thread for computing image embeddings"""

    progress = Signal(int, int, str)   # current, total, message
    batch_complete = Signal(dict)       # Dict[str, np.ndarray]
    finished = Signal(dict)             # Dict[str, np.ndarray]
    error = Signal(str)
    model_loading = Signal()
    model_loaded = Signal()
    status = Signal(str)

    def __init__(
        self,
        image_paths: List[str],
        model_name: str = "clip-ViT-B-32",
        cache: Optional[EmbeddingCache] = None,
        batch_size: int = 512,
        use_gpu: bool = True,
        io_workers: int = 12,
        parent=None
    ):
        super().__init__(parent)
        self.image_paths = image_paths
        self.model_name = model_name
        self.cache = cache
        self.batch_size = batch_size
        self.use_gpu = use_gpu
        self.io_workers = io_workers
        self._is_cancelled = False

    def run(self) -> None:
        try:
            all_embeddings: Dict[str, np.ndarray] = {}
            uncached_paths: List[str] = []

            # Step 1: Check cache
            self.status.emit("Checking cache...")
            self.progress.emit(0, len(self.image_paths), "Checking cache...")

            if self.cache:
                for i, path in enumerate(self.image_paths):
                    if self._is_cancelled:
                        return
                    cached = self.cache.get_embedding(path, self.model_name)
                    if cached is not None:
                        all_embeddings[path] = cached
                    else:
                        uncached_paths.append(path)
                    if (i + 1) % 100 == 0:
                        self.progress.emit(i + 1, len(self.image_paths), "Checking cache...")
            else:
                uncached_paths = list(self.image_paths)

            cache_hits = len(all_embeddings)
            self.status.emit(f"Cache: {cache_hits} hits, {len(uncached_paths)} to compute")

            if self._is_cancelled:
                return

            # Step 2: Load model and compute embeddings for uncached images
            if uncached_paths:
                self.model_loading.emit()
                self.status.emit("Loading CLIP model...")

                engine = EmbeddingEngine(model_name=self.model_name, use_gpu=self.use_gpu)
                engine.load_model()

                self.model_loaded.emit()
                self.status.emit(f"Model loaded on {engine.device}")

                if self._is_cancelled:
                    engine.unload_model()
                    return

                total = len(uncached_paths)

                for batch_start in range(0, total, self.batch_size):
                    if self._is_cancelled:
                        engine.unload_model()
                        return

                    batch_end = min(batch_start + self.batch_size, total)
                    batch_paths = uncached_paths[batch_start:batch_end]

                    batch_embeddings = engine.compute_embeddings_batch(
                        batch_paths,
                        batch_size=len(batch_paths),
                        num_io_workers=self.io_workers
                    )

                    for path, embedding in batch_embeddings.items():
                        if embedding is not None:
                            all_embeddings[path] = embedding
                            if self.cache:
                                self.cache.store_embedding(path, embedding, self.model_name)

                    current = batch_end
                    self.progress.emit(
                        cache_hits + current,
                        len(self.image_paths),
                        f"Computing embeddings ({current}/{total})"
                    )
                    self.batch_complete.emit(batch_embeddings)

                engine.unload_model()

            self.progress.emit(len(self.image_paths), len(self.image_paths), "Complete")
            self.finished.emit(all_embeddings)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self) -> None:
        self._is_cancelled = True
