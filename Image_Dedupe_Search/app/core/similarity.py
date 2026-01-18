"""Cosine similarity computation and duplicate detection"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SimilarityResult:
    """Result of similarity comparison between two images"""
    image1_path: str
    image2_path: str
    similarity_score: float


@dataclass
class DuplicateGroup:
    """Group of similar images"""
    representative: str  # Path to "best" image (highest resolution)
    duplicates: List[str] = field(default_factory=list)  # Paths to duplicate images
    similarity_scores: Dict[str, float] = field(default_factory=dict)  # path -> score

    @property
    def all_images(self) -> List[str]:
        """Get all images in the group including representative"""
        return [self.representative] + self.duplicates

    @property
    def size(self) -> int:
        """Get total number of images in group"""
        return 1 + len(self.duplicates)


class SimilarityEngine:
    """Computes similarity between images using embeddings"""

    def __init__(self, threshold: float = 0.92):
        """
        Initialize similarity engine

        Args:
            threshold: Minimum similarity score to consider images as duplicates (0-1)
        """
        self.threshold = threshold

    def set_threshold(self, threshold: float) -> None:
        """
        Update similarity threshold

        Args:
            threshold: New threshold value (0-1)
        """
        self.threshold = max(0.0, min(1.0, threshold))

    def compute_pairwise_similarity(
        self,
        embeddings: Dict[str, np.ndarray],
        progress_callback: Optional[callable] = None
    ) -> List[SimilarityResult]:
        """
        Compute similarity matrix for all embeddings

        Args:
            embeddings: Dict mapping image path to embedding vector
            progress_callback: Optional callback for progress (current, total)

        Returns:
            List of pairs above threshold, sorted by similarity (highest first)
        """
        if len(embeddings) < 2:
            return []

        paths = list(embeddings.keys())
        n = len(paths)

        # Stack embeddings into matrix
        matrix = np.vstack([embeddings[p] for p in paths])

        # Compute all pairwise similarities at once
        # This is much faster than computing pairs individually
        similarity_matrix = cosine_similarity(matrix)

        # Extract pairs above threshold
        results = []
        total_pairs = (n * (n - 1)) // 2
        current_pair = 0

        for i in range(n):
            for j in range(i + 1, n):
                score = float(similarity_matrix[i, j])

                if score >= self.threshold:
                    results.append(SimilarityResult(
                        image1_path=paths[i],
                        image2_path=paths[j],
                        similarity_score=score
                    ))

                current_pair += 1
                if progress_callback and current_pair % 1000 == 0:
                    progress_callback(current_pair, total_pairs)

        if progress_callback:
            progress_callback(total_pairs, total_pairs)

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        return results

    def find_duplicate_groups(
        self,
        similarities: List[SimilarityResult],
        image_metadata: Optional[Dict[str, dict]] = None
    ) -> List[DuplicateGroup]:
        """
        Group similar images using union-find algorithm

        Args:
            similarities: List of similarity results from compute_pairwise_similarity
            image_metadata: Optional dict mapping path to metadata (with 'width', 'height', 'file_size')

        Returns:
            List of DuplicateGroup objects
        """
        if not similarities:
            return []

        # Build union-find structure
        parent: Dict[str, str] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Union all similar pairs
        for sim in similarities:
            union(sim.image1_path, sim.image2_path)

        # Group images by their root
        groups: Dict[str, List[str]] = {}
        for sim in similarities:
            for path in [sim.image1_path, sim.image2_path]:
                root = find(path)
                if root not in groups:
                    groups[root] = set()
                groups[root].add(path)

        # Convert to list format
        for root in groups:
            groups[root] = list(groups[root])

        # Build similarity score map
        score_map: Dict[Tuple[str, str], float] = {}
        for sim in similarities:
            key = tuple(sorted([sim.image1_path, sim.image2_path]))
            score_map[key] = sim.similarity_score

        # Create DuplicateGroup objects
        result: List[DuplicateGroup] = []

        for root, members in groups.items():
            if len(members) < 2:
                continue

            # Select representative (best quality image)
            representative = self._select_representative(members, image_metadata)

            # Build duplicates list and scores
            duplicates = [m for m in members if m != representative]
            similarity_scores = {}

            for dup in duplicates:
                key = tuple(sorted([representative, dup]))
                if key in score_map:
                    similarity_scores[dup] = score_map[key]
                else:
                    # Find any similarity score for this duplicate
                    for other in members:
                        if other != dup:
                            key = tuple(sorted([other, dup]))
                            if key in score_map:
                                similarity_scores[dup] = score_map[key]
                                break

            group = DuplicateGroup(
                representative=representative,
                duplicates=sorted(duplicates),
                similarity_scores=similarity_scores
            )
            result.append(group)

        # Sort groups by size (largest first)
        result.sort(key=lambda g: g.size, reverse=True)

        return result

    def _select_representative(
        self,
        images: List[str],
        metadata: Optional[Dict[str, dict]]
    ) -> str:
        """
        Select the best quality image as representative

        Args:
            images: List of image paths
            metadata: Optional metadata dict

        Returns:
            Path to the representative image
        """
        if not metadata:
            return images[0]

        def get_score(path: str) -> Tuple[int, int]:
            """Get quality score for sorting (megapixels, file_size)"""
            if path not in metadata:
                return (0, 0)
            meta = metadata[path]
            width = meta.get('width', 0)
            height = meta.get('height', 0)
            size = meta.get('file_size', 0)
            return (width * height, size)

        # Sort by quality and return best
        sorted_images = sorted(images, key=get_score, reverse=True)
        return sorted_images[0]

    def get_similarity_score(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1)
        """
        # Reshape for sklearn
        e1 = embedding1.reshape(1, -1)
        e2 = embedding2.reshape(1, -1)

        score = cosine_similarity(e1, e2)[0, 0]
        return float(score)
