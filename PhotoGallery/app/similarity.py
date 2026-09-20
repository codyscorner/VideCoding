"""Pure fingerprint computation for the "Find Similar" feature.

Two signals are computed per image:
  - A face encoding (via face_recognition) for identity matching when the
    reference image contains a detectable face.
  - A dHash + color histogram for general visual similarity (near-duplicate,
    same scene/composition/palette) used when no face is available, either
    in the reference image or the candidate.

Kept dependency-light on purpose: only PIL/numpy/cv2/face_recognition, all
of which are already bundled elsewhere in this app or its sibling
FaceFinder project — no CLIP/torch, which would bloat the EXE.
"""

from typing import List, Tuple

import numpy as np
from PIL import Image

HASH_SIZE = 8          # -> 64-bit dHash
FINGERPRINT_MAX_DIM = 1200  # resize cap before face detection (speed/accuracy tradeoff)
HIST_SIZE = 64         # square thumbnail used for the color histogram

Fingerprint = Tuple[int, np.ndarray, List[np.ndarray]]  # (phash, hist, face_encodings)


def _compute_dhash(gray_img: Image.Image) -> int:
    small = gray_img.resize((HASH_SIZE + 1, HASH_SIZE), Image.LANCZOS)
    pixels = np.asarray(small, dtype=np.int16)
    diff = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return value


def _compute_color_hist(rgb_img: Image.Image) -> np.ndarray:
    import cv2
    small = rgb_img.resize((HIST_SIZE, HIST_SIZE), Image.LANCZOS)
    arr = np.asarray(small)
    hsv = cv2.cvtColor(arr[:, :, ::-1], cv2.COLOR_BGR2HSV)  # PIL is RGB, cv2 wants BGR
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten().astype(np.float32)


def compute_fingerprint(path: str) -> Fingerprint:
    """Compute (phash, color histogram, face encodings) for one image file.

    Run in a worker process/thread — safe to call standalone since it only
    touches the given path.
    """
    with Image.open(path) as raw:
        img = raw.convert("RGB")
        if max(img.size) > FINGERPRINT_MAX_DIM:
            ratio = FINGERPRINT_MAX_DIM / max(img.size)
            img = img.resize(
                (max(1, int(img.width * ratio)), max(1, int(img.height * ratio))),
                Image.LANCZOS,
            )
        phash = _compute_dhash(img.convert("L"))
        hist = _compute_color_hist(img)
        faces: List[np.ndarray] = []
        try:
            import face_recognition
            encodings = face_recognition.face_encodings(np.asarray(img))
            faces = [e.astype(np.float32) for e in encodings]
        except Exception:
            faces = []
    return phash, hist, faces


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def hist_similarity(a: np.ndarray, b: np.ndarray) -> float:
    import cv2
    return float(cv2.compareHist(a, b, cv2.HISTCMP_CORREL))


def visual_similarity_score(phash_a: int, hist_a: np.ndarray, phash_b: int, hist_b: np.ndarray) -> float:
    """Combined 0..1 score — higher is more similar."""
    hash_score = 1.0 - (hamming_distance(phash_a, phash_b) / (HASH_SIZE * HASH_SIZE))
    hist_score = max(0.0, hist_similarity(hist_a, hist_b))
    return 0.6 * hash_score + 0.4 * hist_score


def face_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))
