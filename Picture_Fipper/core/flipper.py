"""
core/flipper.py — Horizontal image flip and save to output folder.
"""
from pathlib import Path
from PIL import Image


def flip_and_save(image_path: Path, output_dir: Path) -> Path:
    """
    Flip *image_path* horizontally and write it to *output_dir*
    with the same filename.  Returns the output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / image_path.name
    with Image.open(image_path) as img:
        img.transpose(Image.FLIP_LEFT_RIGHT).save(out_path)
    return out_path


def copy_without_flip(image_path: Path, output_dir: Path) -> Path:
    """Copy image unchanged to *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / image_path.name
    with Image.open(image_path) as img:
        img.save(out_path)
    return out_path
