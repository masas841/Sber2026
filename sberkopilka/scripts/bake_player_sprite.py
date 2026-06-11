#!/usr/bin/env python3
"""Копилка (image 2090010243 / 25:172): круговая маска как в Figma."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "assets" / "figma" / "shared" / "ecfb971636fafb1d3d324a0e161c02ca67c0f588.png"
OUT = ROOT / "web" / "assets" / "figma" / "shared" / "player-field-masked.png"

# Figma: rounded-[1000px] overflow-hidden, контейнер 28×29
MASK_W = 28
MASK_H = 29
IMG_SCALE_W = 1.4753
IMG_SCALE_H = 1.4464
IMG_LEFT = -0.2376
IMG_TOP = -0.1776
BAKE_SCALE = 4


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    cw = int(MASK_W * BAKE_SCALE)
    ch = int(MASK_H * BAKE_SCALE)
    layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

    img_w = int(MASK_W * IMG_SCALE_W * BAKE_SCALE)
    img_h = int(MASK_H * IMG_SCALE_H * BAKE_SCALE)
    dx = int(MASK_W * IMG_LEFT * BAKE_SCALE)
    dy = int(MASK_H * IMG_TOP * BAKE_SCALE)
    fitted = src.resize((img_w, img_h), Image.Resampling.LANCZOS)
    layer.paste(fitted, (dx, dy), fitted)

    mask = Image.new("L", (cw, ch), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, cw - 1, ch - 1), fill=255)
    layer.putalpha(Image.composite(layer.split()[3], Image.new("L", (cw, ch), 0), mask))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    layer.save(OUT, optimize=True)
    print(f"wrote {OUT.name} ({cw}x{ch})")


if __name__ == "__main__":
    main()
