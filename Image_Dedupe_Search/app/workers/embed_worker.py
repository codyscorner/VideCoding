"""Worker thread for computing image embeddings"""

from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Optional
import numpy as np

from app.core.embeddings import EmbeddingEngine
from app.core.cache import EmbeddingCache


class EmbedWorker(QThread):
    """Worker thread for computing image embeddings"""

    # Signals
    progress = Signal(int, int, str)  # current, total, current_file
    batch_complete = Signal(dict)  # Dict[str, np.ndarray] - batch results
    finished = Signal(dict)  # Dict[str, np.ndarray] - all embeddings
    error = Signal(str)  # Error message
    model_loading = Signal()  # Emitted when starting model load
    model_loaded = Signal()  # Emitted when model is ready
    status = Signal(str)  # Status message

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
        """
        Initialize embed worker

        Args:
            image_paths: List of image file paths to process
            model_name: Name of the CLIP model to use
            cache: Optional embedding cache for retrieving/storing embeddings
            batch_size: Number of images per GPU batch
            use_gpu: Whether to use GPU if available
            io_workers: Number of parallel threads for loading images from disk
            parent: Parent QObject
        """
        super().__init__(parent)
        self.image_paths = image_paths
        self.model_name = model_name
        self.cache = cache
        self.batch_size = batch_size
        self.use_gpu = use_gpu
        self.io_workers = io_workers
        self._is_cancelled = False

    def run(self) -> None:
        """
        Compute embeddings for all images

        1. Check cache for existing embeddings
        2. Load model
        3. Process uncached images in batches
        4. Store new embeddings in cache
        5. Emit finished with all embeddings
        """
        try:
            all_embeddings: Dict[str, np.ndarray] = {}
            uncached_paths: List[str] = []

            # Step 1: Check cache for existing embeddings
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

            # Step 2: If there are uncached images, load model and process
            if uncached_paths:
                # Load model
                self.model_loading.emit()
                self.status.emit("Loading CLIP model...")

                engine = EmbeddingEngine(
                    model_name=self.model_name,
                    use_gpu=self.use_gpu
                )
                engine.load_model()

                self.model_loaded.emit()
                self.status.emit(f"Model loaded on {engine.device}")

                if self._is_cancelled:
                    engine.unload_model()
                    return

                # Step 3: Process uncached images in batches
                total = len(uncached_paths)

                for batch_start in range(0, total, self.batch_size):
                    if self._is_cancelled:
                        engine.unload_model()
                        return

                    batch_end = min(batch_start + self.batch_size, total)
                    batch_paths = uncached_paths[batch_start:batch_end]

                    # Compute embeddings for batch (parallel image loading + GPU)
                    batch_embeddings = engine.compute_embeddings_batch(
                        batch_paths,
                        batch_size=len(batch_paths),
                        num_io_workers=self.io_workers
                    )

                    # Store results and update cache
                    for path, embedding in batch_embeddings.items():
                        if embedding is not None:
                            all_embeddings[path] = embedding

                            # Store in cache
                            if self.cache:
                                self.cache.store_embedding(path, embedding, self.model_name)

                    # Emit progress
                    current = batch_end
                    self.progress.emit(
                        cache_hits + current,
                        len(self.image_paths),
                        f"Computing embeddings ({current}/{total})"
                    )

                    # Emit batch results
                    self.batch_complete.emit(batch_embeddings)

                # Cleanup
                engine.unload_model()

            # Step 4: Emit final results
            self.progress.emit(
                len(self.image_paths),
                len(self.image_paths),
                "Complete"
            )
            self.finished.emit(all_embeddings)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Request cancellation"""
        self._is_cancelled = True
