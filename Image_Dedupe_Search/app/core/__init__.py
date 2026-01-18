"""Core modules for image processing and similarity computation"""

from .image_utils import ImageUtils, ImageMetadata, SUPPORTED_EXTENSIONS
from .cache import EmbeddingCache
from .embeddings import EmbeddingEngine
from .similarity import SimilarityEngine, SimilarityResult, DuplicateGroup

__all__ = [
    'ImageUtils',
    'ImageMetadata',
    'SUPPORTED_EXTENSIONS',
    'EmbeddingCache',
    'EmbeddingEngine',
    'SimilarityEngine',
    'SimilarityResult',
    'DuplicateGroup'
]
