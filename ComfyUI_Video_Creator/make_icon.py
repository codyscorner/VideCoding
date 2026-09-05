"""Generate app_icon.ico (dark red film-strip + play triangle) with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size: int = 256) -> Image.Image:
    s = 4  # supersample for smooth edges
    W = size * s
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    r = W * 0.18
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=r, fill=(38, 8, 12, 255))
    d.rounded_rectangle([W * 0.03, W * 0.03, W * 0.97, W * 0.97], radius=r * 0.85,
                        fill=(122, 12, 30, 255))
    d.rounded_rectangle([W * 0.06, W * 0.06, W * 0.94, W * 0.94], radius=r * 0.75,
                        fill=(60, 8, 16, 255))

    # film sprocket holes down both edges
    hole_w, hole_h = W * 0.075, W * 0.085
    n = 5
    for i in range(n):
        y = W * 0.12 + i * (W * 0.76 - hole_h) / (n - 1)
        for x in (W * 0.105, W * 0.895 - hole_w):
            d.rounded_rectangle([x, y, x + hole_w, y + hole_h], radius=hole_w * 0.25, fill=(179, 18, 43, 255))

    # play triangle
    cx, cy = W * 0.52, W * 0.5
    h = W * 0.42
    w = h * 0.9
    pts = [(cx - w * 0.42, cy - h / 2), (cx - w * 0.42, cy + h / 2), (cx + w * 0.58, cy)]
    d.polygon(pts, fill=(244, 230, 230, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    base = render(256)
    out = Path(__file__).parent / "app_icon.ico"
    base.save(out, format="ICO", sizes=[(sz, sz) for sz in SIZES])
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
