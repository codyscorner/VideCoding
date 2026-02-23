"""
core/face_matcher.py — Reference face embedding + position detection via DeepFace.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from deepface import DeepFace

Position = Literal["left", "right", "none", "no_match"]

_MODEL = "Facenet"          # fast, accurate, pure-Python weights
_DETECTOR = "opencv"        # no dlib needed
_DISTANCE_METRIC = "cosine"
_THRESHOLD = 0.40           # cosine distance — lower = stricter


class FaceMatcher:
    """
    Encode a reference face once, then test each image for a match
    and return the matched face's position (left / right).
    """

    def __init__(self, reference_image_path: str | Path) -> None:
        ref = str(reference_image_path)
        # Extract embedding from the reference image
        result = DeepFace.represent(
            img_path=ref,
            model_name=_MODEL,
            detector_backend=_DETECTOR,
            enforce_detection=True,
        )
        # represent() returns a list of dicts; take the first (largest) face
        self._ref_embedding = np.array(result[0]["embedding"])

    # ------------------------------------------------------------------

    def detect(self, image_path: str | Path, image_width: int | None = None) -> Position:
        """
        Return:
          'left'     — reference face found and its centre is left of midpoint
          'right'    — reference face found and its centre is right of midpoint
          'no_match' — image processed but reference face not found
          'none'     — no face detected at all
        """
        path = str(image_path)

        try:
            faces = DeepFace.represent(
                img_path=path,
                model_name=_MODEL,
                detector_backend=_DETECTOR,
                enforce_detection=False,   # returns [] instead of raising
            )
        except Exception:
            return "none"

        if not faces:
            return "none"

        # Get image width if not provided
        if image_width is None:
            from PIL import Image
            with Image.open(image_path) as img:
                image_width = img.width

        # Find the face whose embedding best matches the reference
        best_face = None
        best_distance = float("inf")

        for face in faces:
            emb = np.array(face["embedding"])
            # Cosine distance
            distance = float(
                1 - np.dot(self._ref_embedding, emb) /
                (np.linalg.norm(self._ref_embedding) * np.linalg.norm(emb) + 1e-9)
            )
            if distance < best_distance:
                best_distance = distance
                best_face = face

        if best_distance > _THRESHOLD:
            return "no_match"

        # facial_area keys: x, y, w, h
        area = best_face.get("facial_area", {})
        x = area.get("x", 0)
        w = area.get("w", 0)
        x_center = x + w / 2

        return "left" if x_center < image_width / 2 else "right"
