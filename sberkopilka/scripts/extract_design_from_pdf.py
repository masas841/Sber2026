# -*- coding: utf-8 -*-
"""
Извлечение растров из PDF макета ИнвестКопилка в PNG с альфа-каналом.

Использование:
  python scripts/extract_design_from_pdf.py
  python scripts/extract_design_from_pdf.py --pdf path/to/file.pdf --out web/assets/design
"""
from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = ROOT.parent / "docs" / "design" / "ИнвестКопилка.pdf"
DEFAULT_OUT = ROOT / "web" / "assets" / "design"

# Целевой экран LED
SCREEN_W = 504
SCREEN_H = 672


def pixmap_to_png_bytes(pix: fitz.Pixmap) -> bytes:
    """Pixmap -> PNG bytes, всегда RGBA."""
    if pix.alpha:
        conv = pix
    else:
        conv = fitz.Pixmap(fitz.csRGB, pix)
    return conv.tobytes("png")


def extract_with_smask(doc: fitz.Document, xref: int, smask: int) -> fitz.Pixmap | None:
    try:
        pix = fitz.Pixmap(doc, xref)
    except Exception:
        return None
    if smask > 0:
        try:
            mask = fitz.Pixmap(doc, smask)
            pix = fitz.Pixmap(pix, mask)
        except Exception:
            pass
    return pix


def white_to_alpha(im: Image.Image, threshold: int = 248) -> Image.Image:
    """Для JPEG без маски: белый фон -> прозрачный (осторожно, только мелкие UI)."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (r, g, b, 0)
    return im


def save_pixmap_png(pix: fitz.Pixmap, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pix.alpha:
        data = pix.tobytes("png")
        path.write_bytes(data)
        has_alpha = True
    else:
        # RGB -> RGBA PNG
        rgb = Image.open(io.BytesIO(pix.tobytes("png")))
        rgba = rgb.convert("RGBA")
        rgba.save(path, format="PNG")
        has_alpha = False
    return {"path": str(path.as_posix()), "w": pix.width, "h": pix.height, "alpha": has_alpha}


def extract_embedded(doc: fitz.Document, out_dir: Path, min_side: int = 32) -> list[dict]:
    """Все встроенные изображения -> PNG (smask / нативная альфа)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    seen: set[int] = set()

    for page_i, page in enumerate(doc):
        for item in page.get_images(full=True):
            xref = item[0]
            smask = item[1] if len(item) > 1 else 0
            if xref in seen:
                continue
            seen.add(xref)

            pix = extract_with_smask(doc, xref, smask)
            if pix is None:
                continue
            if pix.width < min_side or pix.height < min_side:
                pix = None
                continue

            name = f"emb-{xref:05d}-{pix.width}x{pix.height}.png"
            meta = save_pixmap_png(pix, out_dir / name)
            meta.update({"xref": xref, "smask": smask, "page": page_i + 1, "kind": "embedded"})
            catalog.append(meta)
            pix = None

    return catalog


def extract_jpeg_as_transparent_ui(doc: fitz.Document, out_dir: Path, max_side: int = 800) -> list[dict]:
    """
    JPEG без smask: сохранить как PNG, для небольших спрайтов убрать белый фон.
    Полноэкранные JPEG не трогаем (остаются в embedded как opaque PNG).
    """
    ui_dir = out_dir / "ui-cutout"
    ui_dir.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    seen: set[int] = set()

    for page in doc:
        for item in page.get_images(full=True):
            xref = item[0]
            smask = item[1] if len(item) > 1 else 0
            if xref in seen or smask > 0:
                seen.add(xref)
                continue
            seen.add(xref)
            try:
                base = doc.extract_image(xref)
            except Exception:
                continue
            if base["ext"].lower() not in ("jpeg", "jpg"):
                continue
            w, h = base["width"], base["height"]
            if w > max_side or h > max_side:
                continue
            im = Image.open(io.BytesIO(base["image"]))
            im = white_to_alpha(im)
            name = f"ui-{xref:05d}-{w}x{h}.png"
            path = ui_dir / name
            im.save(path, format="PNG")
            catalog.append(
                {
                    "path": str(path.as_posix()),
                    "w": w,
                    "h": h,
                    "alpha": True,
                    "xref": xref,
                    "kind": "ui-cutout",
                }
            )
    return catalog


def extract_screen_crops(doc: fitz.Document, out_dir: Path) -> list[dict]:
    """
    Вырезать фреймы ~504×672 с полотна PDF (прозрачный фон вокруг, alpha=True).
    Ищем размещения картинок близких к целевому соотношению 3:4.
    """
    screens_dir = out_dir / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    page = doc[0]

    placements: list[tuple[fitz.Rect, int]] = []
    for item in page.get_images(full=True):
        xref = item[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            continue
        for rect in rects:
            rw, rh = rect.width, rect.height
            if rw < 400 or rh < 500:
                continue
            ratio = rw / rh
            if 0.68 < ratio < 0.82:  # ~3:4
                placements.append((rect, xref))

    placements.sort(key=lambda t: (round(t[0].y0 / 50), t[0].x0))

    for i, (rect, xref) in enumerate(placements):
        # Рендер области в целевом разрешении
        clip = fitz.Rect(rect)
        scale_x = SCREEN_W / clip.width
        scale_y = SCREEN_H / clip.height
        scale = min(scale_x, scale_y)
        mat = fitz.Matrix(scale, scale)
        try:
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=True)
            im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
        except Exception:
            continue
        out_im = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
        ox = (SCREEN_W - im.width) // 2
        oy = (SCREEN_H - im.height) // 2
        out_im.paste(im, (ox, oy), im)
        name = f"screen-{i + 1:02d}-{int(rect.width)}x{int(rect.height)}.png"
        path = screens_dir / name
        out_im.save(path, format="PNG")
        catalog.append(
            {
                "path": str(path.as_posix()),
                "w": SCREEN_W,
                "h": SCREEN_H,
                "alpha": True,
                "xref": xref,
                "kind": "screen-crop",
                "pdf_rect": [rect.x0, rect.y0, rect.x1, rect.y1],
            }
        )
        if i >= 39:
            break

    return catalog


def extract_page_slices(doc: fitz.Document, out_dir: Path, slice_w: float = 504, slice_h: float = 672) -> list[dict]:
    """
    Резерв: нарезка полотна по сетке slice_w × slice_h (PDF pt ≈ px в макете Figma).
  """
    slices_dir = out_dir / "slices"
    slices_dir.mkdir(parents=True, exist_ok=True)
    page = doc[0]
    catalog: list[dict] = []
    cols = int(page.rect.width // slice_w)
    rows = int(page.rect.height // slice_h)
    idx = 0
    for row in range(rows):
        for col in range(cols):
            x0 = col * slice_w
            y0 = row * slice_h
            clip = fitz.Rect(x0, y0, x0 + slice_w, y0 + slice_h)
            scale_x = SCREEN_W / slice_w
            mat = fitz.Matrix(scale_x, scale_x)
            try:
                pix = page.get_pixmap(matrix=mat, clip=clip, alpha=True)
                im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
                idx += 1
                name = f"slice-r{row}c{col}-{idx:03d}.png"
                path = slices_dir / name
                im.save(path, format="PNG")
                catalog.append(
                    {
                        "path": str(path.as_posix()),
                        "w": im.width,
                        "h": im.height,
                        "alpha": True,
                        "kind": "grid-slice",
                        "grid": [row, col],
                    }
                )
            except Exception:
                continue
    return catalog


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract PNG assets with alpha from design PDF")
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-slices", action="store_true", help="Skip grid slice export")
    args = ap.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    args.out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    print(f"PDF: {args.pdf} pages={len(doc)} size={doc[0].rect.width:.0f}x{doc[0].rect.height:.0f}")

    catalog: list[dict] = []
    print("Extracting embedded images...")
    catalog.extend(extract_embedded(doc, args.out / "embedded"))
    print(f"  embedded: {len([c for c in catalog if c['kind']=='embedded'])}")

    print("UI cutouts (small JPEG -> PNG alpha)...")
    ui = extract_jpeg_as_transparent_ui(doc, args.out)
    catalog.extend(ui)
    print(f"  ui-cutout: {len(ui)}")

    print("Screen crops (3:4 frames)...")
    screens = extract_screen_crops(doc, args.out)
    catalog.extend(screens)
    print(f"  screens: {len(screens)}")

    if not args.no_slices:
        print("Grid slices 504x672...")
        slices = extract_page_slices(doc, args.out)
        catalog.extend(slices)
        print(f"  slices: {len(slices)}")

    manifest = {
        "source_pdf": str(args.pdf.as_posix()),
        "screen_target": [SCREEN_W, SCREEN_H],
        "page_size": [doc[0].rect.width, doc[0].rect.height],
        "assets": catalog,
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    doc.close()
    print(f"Done: {len(catalog)} assets -> {args.out}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
