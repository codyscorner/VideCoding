"""CLIP embedding engine using sentence-transformers"""

import numpy as np
from PIL import Image
from typing import List, Optional, Callable, Dict, Tuple
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed, Future


class EmbeddingEngine:
    """Computes CLIP embeddings for images using sentence-transformers"""

    def __init__(
        self,
        model_name: str = "clip-ViT-B-32",
        use_gpu: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        """
        Initialize the embedding engine

        Args:
            model_name: Name of the CLIP model to use (sentence-transformers format)
            use_gpu: Whether to use GPU if available
            progress_callback: Optional callback for progress updates (current, total, message)
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.progress_callback = progress_callback
        self.model = None
        self.device = None

    def _determine_device(self) -> str:
        """Determine the best device to use"""
        if self.use_gpu and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load_model(self) -> None:
        """
        Lazy-load the CLIP model (expensive operation)

        This should be called before computing embeddings.
        """
        if self.model is not None:
            return

        # Import here to avoid slow startup
        from sentence_transformers import SentenceTransformer

        self.device = self._determine_device()

        if self.progress_callback:
            self.progress_callback(0, 1, f"Loading {self.model_name} model...")

        self.model = SentenceTransformer(self.model_name)
        self.model.to(self.device)

        if self.progress_callback:
            self.progress_callback(1, 1, f"Model loaded on {self.device}")

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        if not self.is_loaded():
            self.load_model()
        return self.model.get_sentence_embedding_dimension()

    def compute_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        Compute embedding for a single image

        Args:
            image_path: Path to the image file

        Returns:
            Normalized embedding vector or None if image cannot be processed
        """
        if not self.is_loaded():
            self.load_model()

        try:
            # Load image
            image = Image.open(image_path)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Compute embedding
            embedding = self.model.encode(image, convert_to_numpy=True)

            # Normalize
            embedding = self.normalize_embedding(embedding)

            return embedding

        except Exception:
            return None

    def _load_single_image(self, path: str) -> Tuple[str, Optional[Image.Image]]:
        """Load a single image in a thread-safe way"""
        try:
            image = Image.open(path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            # Load the image data into memory (PIL lazy loads)
            image.load()
            return (path, image)
        except Exception:
            return (path, None)

    def _load_images_parallel(
        self,
        image_paths: List[str],
        num_workers: int = 8
    ) -> Tuple[List[str], List[Image.Image], List[str]]:
        """
        Load images in parallel using thread pool

        Args:
            image_paths: List of image paths to load
            num_workers: Number of parallel workers

        Returns:
            Tuple of (valid_paths, images, failed_paths)
        """
        valid_paths = []
        images = []
        failed_paths = []

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(self._load_single_image, path): path
                for path in image_paths
            }

            for future in as_completed(futures):
                path, image = future.result()
                if image is not None:
                    valid_paths.append(path)
                    images.append(image)
                else:
                    failed_paths.append(path)

        return valid_paths, images, failed_paths

    def compute_embeddings_batch(
        self,
        image_paths: List[str],
        batch_size: int = 32,
        num_io_workers: int = 8
    ) -> Dict[str, Optional[np.ndarray]]:
        """
        Compute embeddings for multiple images in batches with prefetching.

        Uses double-buffering: loads next batch from disk while GPU processes current batch.

        Args:
            image_paths: List of image file paths
            batch_size: Number of images to process per GPU batch
            num_io_workers: Number of parallel threads for image loading

        Returns:
            Dict mapping path to embedding (or None if failed)
        """
        if not self.is_loaded():
            self.load_model()

        results: Dict[str, Optional[np.ndarray]] = {}
        total = len(image_paths)

        if total == 0:
            return results

        # Create persistent thread pool for prefetching
        with ThreadPoolExecutor(max_workers=num_io_workers) as io_executor:
            # Split into batches
            batches = []
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batches.append(image_paths[batch_start:batch_end])

            # Start loading first batch
            current_future = io_executor.submit(
                self._load_images_parallel_internal, batches[0], num_io_workers
            )

            for i, batch_paths in enumerate(batches):
                # Wait for current batch to finish loading
                valid_paths, images, failed_paths = current_future.result()

                # Start prefetching next batch while we process current
                next_future = None
                if i + 1 < len(batches):
                    next_future = io_executor.submit(
                        self._load_images_parallel_internal, batches[i + 1], num_io_workers
                    )

                # Mark failed paths
                for path in failed_paths:
                    results[path] = None

                if images:
                    try:
                        # Compute embeddings for batch on GPU
                        embeddings = self.model.encode(
                            images,
                            batch_size=len(images),
                            convert_to_numpy=True,
                            show_progress_bar=False
                        )

                        # Normalize and store results
                        for path, embedding in zip(valid_paths, embeddings):
                            results[path] = self.normalize_embedding(embedding)

                    except Exception:
                        # If batch fails, mark all as None
                        for path in valid_paths:
                            results[path] = None

                    # Free image memory immediately
                    del images

                # Move to next batch
                if next_future is not None:
                    current_future = next_future

                # Report progress
                if self.progress_callback:
                    current = min((i + 1) * batch_size, total)
                    self.progress_callback(
                        current,
                        total,
                        f"Processed {current}/{total} images"
                    )

        return results

    def _load_images_parallel_internal(
        self,
        image_paths: List[str],
        num_workers: int
    ) -> Tuple[List[str], List[Image.Image], List[str]]:
        """Internal method for loading images - used by prefetcher"""
        valid_paths = []
        images = []
        failed_paths = []

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(self._load_single_image, path): path
                for path in image_paths
            }

            for future in as_completed(futures):
                path, image = future.result()
                if image is not None:
                    valid_paths.append(path)
                    images.append(image)
                else:
                    failed_paths.append(path)

        return valid_paths, images, failed_paths

    @staticmethod
    def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        """
        L2 normalize embedding for cosine similarity

        Args:
            embedding: Embedding vector to normalize

        Returns:
            Normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding

    def unload_model(self) -> None:
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None

            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()
