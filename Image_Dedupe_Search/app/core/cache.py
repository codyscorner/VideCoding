"""SQLite-based embedding cache with stale entry detection"""

import sqlite3
import numpy as np
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import os


class EmbeddingCache:
    """SQLite cache for image embeddings"""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        file_hash TEXT NOT NULL,
        modified_time REAL NOT NULL,
        file_size INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        embedding_dim INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_file_path ON embeddings(file_path);
    CREATE INDEX IF NOT EXISTS idx_file_hash ON embeddings(file_hash);
    CREATE INDEX IF NOT EXISTS idx_model_name ON embeddings(model_name);
    """

    def __init__(self, db_path: str = "./data/cache.sqlite"):
        """
        Initialize the embedding cache

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establish database connection and create schema if needed"""
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        # Create schema
        cursor = self.connection.cursor()
        cursor.executescript(self.SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def _ensure_connected(self) -> None:
        """Ensure database connection is established"""
        if self.connection is None:
            self.connect()

    def get_embedding(
        self,
        file_path: str,
        model_name: str
    ) -> Optional[np.ndarray]:
        """
        Get cached embedding if valid (file not modified)

        Args:
            file_path: Path to the image file
            model_name: Name of the model that generated the embedding

        Returns:
            Embedding array or None if cache miss or stale
        """
        self._ensure_connected()

        try:
            # Get current file stats
            path = Path(file_path)
            if not path.exists():
                return None

            stat = path.stat()
            current_mtime = stat.st_mtime
            current_size = stat.st_size

            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT embedding, embedding_dim, modified_time, file_size
                FROM embeddings
                WHERE file_path = ? AND model_name = ?
            """, (str(path.absolute()), model_name))

            row = cursor.fetchone()
            if row is None:
                return None

            # Check if file has been modified
            cached_mtime = row['modified_time']
            cached_size = row['file_size']

            if abs(current_mtime - cached_mtime) > 1.0 or current_size != cached_size:
                # File has been modified, cache is stale
                return None

            # Deserialize embedding
            embedding = self._deserialize_embedding(
                row['embedding'],
                row['embedding_dim']
            )
            return embedding

        except Exception:
            return None

    def store_embedding(
        self,
        file_path: str,
        embedding: np.ndarray,
        model_name: str
    ) -> None:
        """
        Store embedding in cache

        Args:
            file_path: Path to the image file
            embedding: Embedding array to store
            model_name: Name of the model that generated the embedding
        """
        self._ensure_connected()

        try:
            path = Path(file_path)
            stat = path.stat()

            # Compute file hash for additional verification
            file_hash = self._compute_file_hash(file_path)

            # Serialize embedding
            embedding_blob = self._serialize_embedding(embedding)

            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings
                (file_path, file_hash, modified_time, file_size, embedding, embedding_dim, model_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(path.absolute()),
                file_hash,
                stat.st_mtime,
                stat.st_size,
                embedding_blob,
                len(embedding),
                model_name,
                datetime.now().isoformat()
            ))
            self.connection.commit()

        except Exception:
            pass  # Silently fail on cache write errors

    def get_embeddings_batch(
        self,
        file_paths: List[str],
        model_name: str
    ) -> Dict[str, Optional[np.ndarray]]:
        """
        Get multiple embeddings, returning None for cache misses

        Args:
            file_paths: List of image file paths
            model_name: Name of the model

        Returns:
            Dict mapping path to embedding (or None if not cached/stale)
        """
        results = {}
        for path in file_paths:
            results[path] = self.get_embedding(path, model_name)
        return results

    def store_embeddings_batch(
        self,
        embeddings: Dict[str, np.ndarray],
        model_name: str
    ) -> None:
        """
        Store multiple embeddings in cache

        Args:
            embeddings: Dict mapping file path to embedding
            model_name: Name of the model
        """
        for path, embedding in embeddings.items():
            self.store_embedding(path, embedding, model_name)

    def invalidate_stale_entries(self) -> int:
        """
        Remove entries for files that no longer exist or were modified

        Returns:
            Number of entries removed
        """
        self._ensure_connected()

        cursor = self.connection.cursor()
        cursor.execute("SELECT id, file_path, modified_time, file_size FROM embeddings")

        stale_ids = []
        for row in cursor.fetchall():
            path = Path(row['file_path'])
            if not path.exists():
                stale_ids.append(row['id'])
            else:
                stat = path.stat()
                if (abs(stat.st_mtime - row['modified_time']) > 1.0 or
                    stat.st_size != row['file_size']):
                    stale_ids.append(row['id'])

        if stale_ids:
            placeholders = ','.join('?' * len(stale_ids))
            cursor.execute(f"DELETE FROM embeddings WHERE id IN ({placeholders})", stale_ids)
            self.connection.commit()

        return len(stale_ids)

    def clear(self) -> None:
        """Clear all cached embeddings"""
        self._ensure_connected()

        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM embeddings")
        self.connection.commit()

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics

        Returns:
            Dict with 'total_entries' and 'total_size_bytes'
        """
        self._ensure_connected()

        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM embeddings")
        count = cursor.fetchone()['count']

        cursor.execute("SELECT SUM(LENGTH(embedding)) as size FROM embeddings")
        row = cursor.fetchone()
        size = row['size'] if row['size'] else 0

        return {
            'total_entries': count,
            'total_size_bytes': size
        }

    @staticmethod
    def _serialize_embedding(embedding: np.ndarray) -> bytes:
        """
        Convert numpy array to bytes for storage

        Args:
            embedding: Numpy array to serialize

        Returns:
            Bytes representation
        """
        return embedding.astype(np.float32).tobytes()

    @staticmethod
    def _deserialize_embedding(data: bytes, dim: int) -> np.ndarray:
        """
        Convert bytes back to numpy array

        Args:
            data: Bytes to deserialize
            dim: Dimension of the embedding

        Returns:
            Numpy array
        """
        return np.frombuffer(data, dtype=np.float32).reshape(dim)

    @staticmethod
    def _compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
        """
        Compute MD5 hash of file for change detection

        Only reads first and last chunks for performance on large files.

        Args:
            file_path: Path to file
            chunk_size: Size of chunks to read

        Returns:
            MD5 hash string
        """
        hasher = hashlib.md5()

        try:
            file_size = os.path.getsize(file_path)

            with open(file_path, 'rb') as f:
                # Read first chunk
                hasher.update(f.read(chunk_size))

                # Read last chunk if file is large enough
                if file_size > chunk_size * 2:
                    f.seek(-chunk_size, 2)  # Seek from end
                    hasher.update(f.read(chunk_size))

            return hasher.hexdigest()
        except Exception:
            return ""
