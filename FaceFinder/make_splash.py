"""Regenerate splash.png with the current version from main.py.

Run before building the EXE so the splash version matches the app:
    python make_splash.py
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
WIDTH, HEIGHT = 400, 250
BG_COLOR = (26, 26, 46)        # dark navy, matches previous splash
TITLE_COLOR = (255, 255, 255)
SUBTITLE_COLOR = (150, 150, 170)
VERSION_COLOR = (110, 110, 130)


def get_version() -> str:
    text = (SCRIPT_DIR / "main.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("VERSION not found in main.py")
    return match.group(1)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def main():
    version = get_version()
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    def center_text(y: int, text: str, font, color):
        w = draw.textlength(text, font=font)
        draw.text(((WIDTH - w) / 2, y), text, font=font, fill=color)

    center_text(70, "FaceFinder", load_font(36, bold=True), TITLE_COLOR)
    center_text(125, "Face Recognition Search Tool", load_font(14), SUBTITLE_COLOR)
    center_text(155, f"v{version}", load_font(13), VERSION_COLOR)

    out = SCRIPT_DIR / "splash.png"
    img.save(out, "PNG")
    print(f"Wrote {out} ({WIDTH}x{HEIGHT}) for v{version}")


if __name__ == "__main__":
    main()
