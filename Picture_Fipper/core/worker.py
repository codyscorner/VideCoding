"""
core/worker.py — Background QThread worker: scan → detect → flip.
Supports two modes:
  - YOLO mode (default): detect any person
  - Face mode: match a specific reference face
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.scanner import scan_folder
from core.flipper import flip_and_save, copy_without_flip


class FlipWorker(QThread):
    """Runs scan → detect → flip in a background thread."""

    progress = Signal(int)       # 0–100
    log_message = Signal(str)    # log text
    status_message = Signal(str) # status bar text
    finished = Signal(int, int)  # (flipped_count, skipped_count)

    def __init__(
        self,
        folder: str,
        output_dir: str,
        model_path: str,
        reference_face: str | None = None,
        target_side: str = "right",   # "right" or "left"
    ) -> None:
        super().__init__()
        self.folder = folder
        self.output_dir = output_dir
        self.model_path = model_path
        self.reference_face = reference_face
        self.target_side = target_side
        self._abort = False

    # ------------------------------------------------------------------

    def abort(self) -> None:
        self._abort = True

    # ------------------------------------------------------------------

    def run(self) -> None:
        if self.reference_face:
            self._run_face_mode()
        else:
            self._run_yolo_mode()

    # ------------------------------------------------------------------
    # YOLO mode — any person
    # ------------------------------------------------------------------

    def _run_yolo_mode(self) -> None:
        from core.detector import PersonDetector

        flipped = skipped = 0
        self.log_message.emit(f"Mode: detect any person (YOLO) → target side: {self.target_side}")
        self.log_message.emit("Scanning folder…")

        images = scan_folder(self.folder)
        total = len(images)
        if total == 0:
            self.log_message.emit("No images found.")
            self.finished.emit(0, 0)
            return

        self.log_message.emit(f"Found {total} image(s). Loading YOLO model…")
        self.status_message.emit("Loading YOLO model…")

        try:
            detector = PersonDetector(self.model_path)
        except Exception as exc:
            self.log_message.emit(f"[ERROR] Could not load model: {exc}")
            self.status_message.emit("Error — could not load YOLO model.")
            self.finished.emit(0, 0)
            return

        self.log_message.emit("Model loaded. Processing…")
        self.status_message.emit("Processing images…")
        output_dir = Path(self.output_dir)

        for idx, img_path in enumerate(images, 1):
            if self._abort:
                self.log_message.emit("Aborted.")
                break

            rel = img_path.name
            try:
                position = detector.detect(img_path)
                flipped, skipped = self._apply(
                    img_path, output_dir, position, rel, flipped, skipped
                )
            except Exception as exc:
                self.log_message.emit(f"[ERROR]    {rel} — {exc}")
                skipped += 1

            self.progress.emit(int(idx / total * 100))

        self._done(flipped, skipped)

    # ------------------------------------------------------------------
    # Face mode — specific reference face
    # ------------------------------------------------------------------

    def _run_face_mode(self) -> None:
        from core.face_matcher import FaceMatcher

        flipped = skipped = 0
        ref_name = Path(self.reference_face).name
        self.log_message.emit(f"Mode: match reference face ({ref_name}) → target side: {self.target_side}")
        self.log_message.emit("Loading DeepFace model weights (first run may take a moment)…")
        self.status_message.emit("Loading DeepFace model weights…")

        try:
            matcher = FaceMatcher(self.reference_face)
        except Exception as exc:
            self.log_message.emit(f"[ERROR] Could not encode reference face: {exc}")
            self.status_message.emit("Error — could not load model.")
            self.finished.emit(0, 0)
            return

        self.log_message.emit("Model ready. Encoding reference face…")
        self.status_message.emit("Reference face encoded. Starting scan…")
        self.log_message.emit("Reference face encoded. Scanning folder…")
        images = scan_folder(self.folder)
        total = len(images)

        if total == 0:
            self.log_message.emit("No images found.")
            self.finished.emit(0, 0)
            return

        self.log_message.emit(f"Found {total} image(s). Processing…")
        output_dir = Path(self.output_dir)

        for idx, img_path in enumerate(images, 1):
            if self._abort:
                self.log_message.emit("Aborted.")
                break

            rel = img_path.name
            try:
                position = matcher.detect(img_path)

                if position == "none":
                    self.log_message.emit(f"[SKIP]     {rel} — no face detected")
                    skipped += 1
                elif position == "no_match":
                    self.log_message.emit(f"[SKIP]     {rel} — reference face not found")
                    skipped += 1
                else:
                    flipped, skipped = self._apply(
                        img_path, output_dir, position, rel, flipped, skipped
                    )
            except Exception as exc:
                self.log_message.emit(f"[ERROR]    {rel} — {exc}")
                skipped += 1

            self.progress.emit(int(idx / total * 100))

        self._done(flipped, skipped)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _apply(
        self,
        img_path: Path,
        output_dir: Path,
        position: str,
        rel: str,
        flipped: int,
        skipped: int,
    ) -> tuple[int, int]:
        # Flip if person is on the wrong side; copy unchanged if already correct
        needs_flip = (position != self.target_side) and (position in ("left", "right"))

        if position not in ("left", "right"):
            copy_without_flip(img_path, output_dir)
            self.log_message.emit(f"[SKIPPED]  {rel} — no person detected")
            skipped += 1
        elif needs_flip:
            flip_and_save(img_path, output_dir)
            self.log_message.emit(f"[FLIPPED]  {rel} — moved to {self.target_side}")
            flipped += 1
        else:
            copy_without_flip(img_path, output_dir)
            self.log_message.emit(f"[OK]       {rel} — already on {self.target_side}")
            skipped += 1
        return flipped, skipped

    def _done(self, flipped: int, skipped: int) -> None:
        self.log_message.emit(f"Done — {flipped} flipped, {skipped} unchanged/skipped.")
        self.finished.emit(flipped, skipped)
