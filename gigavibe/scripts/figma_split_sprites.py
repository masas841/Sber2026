"""Split Figma raw sprite sheets into individual transparent PNGs."""
from __future__ import annotations

import json
import pathlib

import cv2
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "web" / "assets" / "figma" / "sprites" / "raw"
OUT = ROOT / "web" / "assets" / "figma" / "sprites" / "elements"

# Known grid layouts from visual inspection
GRIDS: dict[str, tuple[int, int]] = {
    "sheet_2090010258": (4, 2),  # 4 cols x 2 rows
}
for name in [
    "image_2090010215",
    "image_2090010220",
    "image_2090010221",
    "image_2090010222",
    "image_2090010223",
    "image_2090010224",
]:
    GRIDS[name] = (3, 3)

MIN_COMPONENT_AREA = 12_000
PADDING = 8


def pil_to_bgra(im: Image.Image) -> np.ndarray:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    arr = np.array(im)
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)


def bgra_to_pil(arr: np.ndarray) -> Image.Image:
    rgba = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
    return Image.fromarray(rgba)


def remove_bg(arr: np.ndarray, mode: str) -> np.ndarray:
    """mode: 'white' | 'black' | 'auto'"""
    bgr = arr[:, :, :3].astype(np.int16)
    if mode == "auto":
        corners = np.vstack(
            [
                bgr[0, 0],
                bgr[0, -1],
                bgr[-1, 0],
                bgr[-1, -1],
            ]
        )
        if corners.mean() > 200:
            mode = "white"
        elif corners.mean() < 40:
            mode = "black"
        else:
            mode = "white"
    if mode == "white":
        mask = (bgr[:, :, 0] > 245) & (bgr[:, :, 1] > 245) & (bgr[:, :, 2] > 245)
    else:
        mask = (bgr[:, :, 0] < 12) & (bgr[:, :, 1] < 12) & (bgr[:, :, 2] < 12)
    out = arr.copy()
    out[mask, 3] = 0
    # soften edges: semi-transparent fringe
    alpha = out[:, :, 3].astype(np.float32)
    fringe = (~mask).astype(np.uint8) * 255
    fringe = cv2.GaussianBlur(fringe, (5, 5), 0)
    out[:, :, 3] = np.minimum(alpha, fringe.astype(np.float32)).astype(np.uint8)
    return out


def trim_transparent(arr: np.ndarray) -> np.ndarray:
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 8)
    if len(xs) == 0:
        return arr
    x0, x1 = max(0, xs.min() - PADDING), min(arr.shape[1], xs.max() + PADDING + 1)
    y0, y1 = max(0, ys.min() - PADDING), min(arr.shape[0], ys.max() + PADDING + 1)
    return arr[y0:y1, x0:x1]


def split_grid(im: Image.Image, cols: int, rows: int) -> list[Image.Image]:
    w, h = im.size
    cell_w, cell_h = w // cols, h // rows
    tiles: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            box = (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
            tiles.append(im.crop(box))
    return tiles


def split_components(im: Image.Image, bg_mode: str) -> list[Image.Image]:
    arr = pil_to_bgra(im)
    arr = remove_bg(arr, bg_mode)
    alpha = arr[:, :, 3]
    _, bin_mask = cv2.threshold(alpha, 16, 255, cv2.THRESH_BINARY)
    bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bin_mask, connectivity=8)
    crops: list[Image.Image] = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < MIN_COMPONENT_AREA:
            continue
        x0 = max(0, x - PADDING)
        y0 = max(0, y - PADDING)
        x1 = min(arr.shape[1], x + w + PADDING)
        y1 = min(arr.shape[0], y + h + PADDING)
        crop = trim_transparent(arr[y0:y1, x0:x1])
        if crop.size == 0:
            continue
        crops.append(bgra_to_pil(crop))
    crops.sort(key=lambda p: (p.size[1] * p.size[0]), reverse=True)
    return crops


def process_one(src: pathlib.Path) -> list[dict]:
    slug = src.stem
    im = Image.open(src)
    entries: list[dict] = []

    if slug in GRIDS:
        cols, rows = GRIDS[slug]
        bg = "white"
        tiles = split_grid(im, cols, rows)
        for idx, tile in enumerate(tiles):
            arr = trim_transparent(remove_bg(pil_to_bgra(tile), bg))
            out_name = f"{slug}_r{idx // cols + 1}c{idx % cols + 1}.png"
            dest = OUT / out_name
            bgra_to_pil(arr).save(dest, optimize=True)
            entries.append(
                {
                    "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
                    "source": slug,
                    "grid": {"row": idx // cols + 1, "col": idx % cols + 1},
                    "size": [int(arr.shape[1]), int(arr.shape[0])],
                }
            )
        return entries

    # Scattered composites on dark bg
    bg_mode = "black" if slug.startswith("composite_") else "auto"
    parts = split_components(im, bg_mode)
    for idx, part in enumerate(parts, start=1):
        out_name = f"{slug}_part{idx:02d}.png"
        dest = OUT / out_name
        part.save(dest, optimize=True)
        entries.append(
            {
                "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "source": slug,
                "part": idx,
                "size": list(part.size),
            }
        )
    return entries


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for src in sorted(RAW.glob("*.png")):
        items = process_one(src)
        manifest.extend(items)
        print(src.name, "->", len(items), "sprites")

    index = {
        "canvas_kiosk": {"width": 1008, "height": 672},
        "camera_frame": {"x": 215, "y": 143, "width": 579, "height": 387},
        "note": "Позиции оверлеев на экране камеры — из Frame 2147223874; видео-фон подключим позже.",
        "sprites": manifest,
    }
    (OUT / "manifest.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total sprites:", len(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
