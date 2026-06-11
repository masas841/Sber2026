#!/usr/bin/env python3
"""Запекает спрайты монстров для поля — кроп/маска как в Figma game 25:141/151/163."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "web" / "assets" / "figma" / "shared"
OUT_IMPULSE = SHARED / "ghost-impulse-field.png"
OUT_FOMO = SHARED / "ghost-fomo-field.png"
OUT_INFLATION = SHARED / "ghost-inflation-field.png"

BAKE = 4


def paste_cover(layer: Image.Image, src: Image.Image, cw: int, ch: int) -> None:
    sw, sh = src.size
    scale = max(cw / sw, ch / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    fitted = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (cw - nw) // 2
    y = (ch - nh) // 2
    layer.paste(fitted, (x, y), fitted)


def bake_fomo() -> None:
    """25:141 — 18 19: overflow crop 154.66% × 225.21%, offset −30.22% / −50.95%."""
    src = Image.open(SHARED / "6efb1b5ba282d7b4bbc5f93a8dbe9bfa74283474.png").convert("RGBA")
    cw, ch = int(37.268 * BAKE), int(34.125 * BAKE)
    layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sw, sh = src.size
    iw = int(cw * 1.5466)
    ih = int(ch * 2.2521)
    fitted = src.resize((iw, ih), Image.Resampling.LANCZOS)
    dx = int(cw * -0.3022)
    dy = int(ch * -0.5095)
    layer.paste(fitted, (dx, dy), fitted)
    layer.save(OUT_FOMO, optimize=True)
    print(f"wrote {OUT_FOMO.name} {layer.size}")


def bake_impulse() -> None:
    """25:151 — ChatGPT bag 40.576×40.576 object-cover."""
    src = Image.open(SHARED / "aa1388805711ad232ced85bc3af05b4dfc2781a6.png").convert("RGBA")
    side = int(40.576 * BAKE)
    layer = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    paste_cover(layer, src, side, side)
    layer.save(OUT_IMPULSE, optimize=True)
    print(f"wrote {OUT_IMPULSE.name} {layer.size}")


def bake_inflation() -> None:
    """25:163 — image 103 в маске image 102 (blob)."""
    src = Image.open(SHARED / "87eccea116ae76e662b837feec4e83cf5f95e45c.png").convert("RGBA")
    mask_w, mask_h = int(36.57 * BAKE), int(32.185 * BAKE)
    img_w, img_h = int(35.465 * BAKE), int(35.085 * BAKE)
    layer = Image.new("RGBA", (mask_w, mask_h), (0, 0, 0, 0))
    fitted = src.resize((img_w, img_h), Image.Resampling.LANCZOS)
    # Figma: -scale-x-100, rotate -21.27°, центр маски
    rotated = fitted.rotate(-21.27, resample=Image.Resampling.BICUBIC, expand=True)
    rotated = rotated.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    rx, ry = rotated.size
    layer.paste(rotated, ((mask_w - rx) // 2, (mask_h - ry) // 2), rotated)

    mask = Image.new("L", (mask_w, mask_h), 0)
    draw = ImageDraw.Draw(mask)
    # blob из SVG viewBox 36.346×25.093 — упрощённый силуэт
    draw.polygon(
        [
            (mask_w * 0.52, mask_h * 0.05),
            (mask_w * 0.95, mask_h * 0.38),
            (mask_w * 0.88, mask_h * 0.82),
            (mask_w * 0.55, mask_h * 0.98),
            (mask_w * 0.12, mask_h * 0.78),
            (mask_w * 0.02, mask_h * 0.42),
            (mask_w * 0.18, mask_h * 0.12),
        ],
        fill=255,
    )
    layer.putalpha(Image.composite(layer.split()[3], Image.new("L", (mask_w, mask_h), 0), mask))
    layer.save(OUT_INFLATION, optimize=True)
    print(f"wrote {OUT_INFLATION.name} {layer.size}")


def main() -> None:
    bake_impulse()
    bake_fomo()
    bake_inflation()


if __name__ == "__main__":
    main()
