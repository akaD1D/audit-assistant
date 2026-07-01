"""Generate the app icon (assets/icon.ico) — a document with a check mark."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "icon.ico"

BLUE = (37, 99, 235, 255)
BLUE_DARK = (30, 64, 175, 255)
WHITE = (255, 255, 255, 255)
GREY = (203, 213, 225, 255)
GREEN = (34, 197, 94, 255)

S = 256


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded blue background.
    d.rounded_rectangle([8, 8, S - 8, S - 8], radius=48, fill=BLUE)

    # White document with a folded corner.
    left, top, right, bottom = 70, 52, 186, 204
    fold = 28
    d.polygon(
        [(left, top), (right - fold, top), (right, top + fold), (right, bottom), (left, bottom)],
        fill=WHITE,
    )
    d.polygon([(right - fold, top), (right, top + fold), (right - fold, top + fold)], fill=GREY)

    # Text lines on the document.
    for i, y in enumerate(range(top + 30, bottom - 20, 22)):
        x2 = right - 22 if i % 2 == 0 else right - 46
        d.line([(left + 18, y), (x2, y)], fill=GREY, width=7)

    # Green check badge (bottom-right).
    cx, cy, r = 176, 186, 34
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN, outline=WHITE, width=5)
    d.line([(cx - 15, cy), (cx - 4, cy + 12)], fill=WHITE, width=7)
    d.line([(cx - 4, cy + 12), (cx + 16, cy - 12)], fill=WHITE, width=7)

    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = draw()
    img.save(OUT, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
