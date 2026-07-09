"""Destructive image edit operations: rotate and crop, saved via Pillow
with EXIF/ICC metadata preserved where the format supports it."""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

# Formats Pillow can write back with an `exif` kwarg
_EXIF_FORMATS = {".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".png"}


def apply_edits(
    src_path: str,
    rotation: int = 0,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
    dest_path: Optional[str] = None,
) -> str:
    """Rotate (clockwise degrees, multiple of 90) then crop, and save.

    `crop_box` is (left, top, right, bottom) in the coordinate space of the
    already-rotated image — matching what the viewer displays.
    Returns the path written.
    """
    dest = dest_path or src_path
    rotation = rotation % 360

    with Image.open(src_path) as img:
        fmt = img.format
        exif = img.info.get("exif")
        icc = img.info.get("icc_profile")

        if rotation:
            # PIL rotates counter-clockwise; our rotation is clockwise
            img = img.rotate(-rotation, expand=True)

        if crop_box:
            left, top, right, bottom = crop_box
            left = max(0, min(left, img.width))
            top = max(0, min(top, img.height))
            right = max(left + 1, min(right, img.width))
            bottom = max(top + 1, min(bottom, img.height))
            img = img.crop((left, top, right, bottom))

        save_kwargs = {}
        if Path(dest).suffix.lower() in _EXIF_FORMATS:
            if exif:
                save_kwargs["exif"] = exif
            if icc:
                save_kwargs["icc_profile"] = icc
        if fmt == "JPEG":
            save_kwargs["quality"] = 95
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

        img.save(dest, format=fmt if dest == src_path else None, **save_kwargs)

    return dest
