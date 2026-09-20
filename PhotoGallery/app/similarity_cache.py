"""SQLite-backed cache of per-image similarity fingerprints, keyed by
absolute path + mtime + size so unchanged files never need to be
reprocessed on a later scan of the same folder."""

import pickle
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.similarity import Fingerprint

_SQLITE_MAX_VARS = 500  # stay well under SQLite's default 999-parameter limit


class SimilarityCache:
    def __init__(self, db_file: Path):
        self.db_file = db_file
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_file), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS fingerprints (
                path TEXT PRIMARY KEY,
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                phash INTEGER NOT NULL,
                hist BLOB NOT NULL,
                faces BLOB
            )"""
        )
        self._conn.commit()

    @staticmethod
    def _key(path: str) -> str:
        return str(Path(path).resolve())

    def get(self, path: str, mtime: float, size: int) -> Optional[Fingerprint]:
        with self._lock:
            row = self._conn.execute(
                "SELECT mtime, size, phash, hist, faces FROM fingerprints WHERE path=?",
                (self._key(path),),
            ).fetchone()
        if row is None:
            return None
        row_mtime, row_size, phash, hist_blob, faces_blob = row
        if row_mtime != mtime or row_size != size:
            return None
        hist = np.frombuffer(hist_blob, dtype=np.float32)
        faces: List[np.ndarray] = pickle.loads(faces_blob) if faces_blob else []
        return phash, hist, faces

    def get_many(self, paths: List[str]) -> Dict[str, Fingerprint]:
        """Bulk-load fingerprints for many paths in a handful of queries instead
        of one round-trip per file — matters when ranking against 10k+ images.
        Does NOT validate mtime/size (callers scanning a live folder should
        treat this as "probably still fresh"; use get() when staleness matters)."""
        keys = [self._key(p) for p in paths]
        key_to_path = dict(zip(keys, paths))
        results: Dict[str, Fingerprint] = {}
        with self._lock:
            for i in range(0, len(keys), _SQLITE_MAX_VARS):
                chunk = keys[i:i + _SQLITE_MAX_VARS]
                placeholders = ",".join("?" * len(chunk))
                rows = self._conn.execute(
                    f"SELECT path, phash, hist, faces FROM fingerprints WHERE path IN ({placeholders})",
                    chunk,
                ).fetchall()
                for key, phash, hist_blob, faces_blob in rows:
                    hist = np.frombuffer(hist_blob, dtype=np.float32)
                    faces: List[np.ndarray] = pickle.loads(faces_blob) if faces_blob else []
                    results[key_to_path[key]] = (phash, hist, faces)
        return results

    def put(self, path: str, mtime: float, size: int, fingerprint: Fingerprint) -> None:
        phash, hist, faces = fingerprint
        faces_blob = pickle.dumps(faces) if faces else None
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO fingerprints (path, mtime, size, phash, hist, faces) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._key(path), mtime, size, int(phash), hist.astype(np.float32).tobytes(), faces_blob),
            )

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.commit()
            self._conn.close()
