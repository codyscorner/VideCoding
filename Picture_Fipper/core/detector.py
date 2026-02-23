"""
core/detector.py — YOLO-based person position detector.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from ultralytics import YOLO

Position = Literal["left", "right", "none"]

# YOLO class index for "person"
_PERSON_CLASS = 0


class PersonDetector:
    """Load a YOLO model once and classify the dominant person's position."""

    def __init__(self, model_path: str | Path) -> None:
        self._model = YOLO(str(model_path))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image_path: str | Path) -> Position:
        """
        Run inference on *image_path* and return:
          'left'  — largest detected person's centre is left of image midpoint
          'right' — largest detected person's centre is right of image midpoint
          'none'  — no person detected
        """
        results = self._model(
            str(image_path),
            classes=[_PERSON_CLASS],  # only detect persons
            verbose=False,
        )

        # results is a list with one element per image
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return "none"

        # xyxy tensor: shape (N, 4) — x1 y1 x2 y2 in pixel coords
        xyxy = boxes.xyxy.cpu().numpy()   # (N, 4)
        confs = boxes.conf.cpu().numpy()  # (N,)

        # Filter by minimum confidence (optional safety net)
        MIN_CONF = 0.25
        mask = confs >= MIN_CONF
        xyxy = xyxy[mask]
        if len(xyxy) == 0:
            return "none"

        # Pick the largest bounding box by area
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        best = xyxy[areas.argmax()]
        x1, _, x2, _ = best

        # Image width from the original result
        img_width = results[0].orig_shape[1]  # orig_shape = (H, W)

        x_center = (x1 + x2) / 2
        return "left" if x_center < img_width / 2 else "right"
