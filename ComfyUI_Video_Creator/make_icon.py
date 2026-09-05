"""Rebuild app_icon.ico from app_icon_source.png.

The source tile was generated with Z-Image Turbo on ComfyUI (prompt: flat
vector app icon, crimson rounded square, white play triangle, film-strip
perforations, black background). This script crops away the black margin,
rounds the corners to transparency and writes every standard icon size.

    python make_icon.py            # uses app_icon_source.png
    python make_icon.py other.png  # any square-ish PNG on a dark background
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
ROOT = Path(__file__).parent


def autocrop(img: Image.Image, thresh: int = 24) -> Image.Image:
    """Crop away the near-black background around the tile, keeping it square."""
    gray = img.convert("L").point(lambda v: 255 if v > thresh else 0)
    bbox = gray.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    w, h = right - left, bottom - top
    side = max(w, h)
    cx, cy = left + w // 2, top + h // 2
    box = (max(0, cx - side // 2), max(0, cy - side // 2),
           min(img.width, cx + side // 2), min(img.height, cy + side // 2))
    return img.crop(box)


def rounded(img: Image.Image, radius_frac: float = 0.2) -> Image.Image:
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    r = int(min(img.size) * radius_frac)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=r, fill=255)
    out = img.copy()
    out.putalpha(ImageChops.multiply(out.getchannel("A"), mask))
    return out


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "app_icon_source.png"
    dst = ROOT / "app_icon.ico"
    img = rounded(autocrop(Image.open(src).convert("RGB")).resize((512, 512), Image.LANCZOS))
    img.resize((256, 256), Image.LANCZOS).save(dst, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {dst} ({dst.stat().st_size} bytes) from {src.name}")


if __name__ == "__main__":
    main()
