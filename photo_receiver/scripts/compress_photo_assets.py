"""Сжать ассеты Figma для /p/{filename} — WebP под размер на экране 393px (2x retina)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent / "static" / "assets" / "figma"

# max сторона на холсте ~565px → 600px с запасом под 2x
ASSETS: list[tuple[str, int, int]] = [
    ("bg-generation.png", 960, 78),
    ("deco-3-3.png", 560, 82),
    ("deco-4.png", 520, 82),
    ("deco-2.png", 520, 82),
    ("sheet-leaf.png", 640, 80),
    ("flower.png", 280, 82),
]

BG_JPEG_QUALITY = 78


def resize_max(img: Image.Image, max_side: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= max_side:
        return img
    if w >= h:
        nw, nh = max_side, round(h * max_side / w)
    else:
        nw, nh = round(w * max_side / h), max_side
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def save_webp(img: Image.Image, path: Path, quality: int) -> None:
    if img.mode not in {"RGB", "RGBA"}:
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    img.save(path, format="WEBP", quality=quality, method=6)


def compress_one(name: str, max_side: int, quality: int) -> None:
    src = ROOT / name
    if not src.is_file():
        print(f"SKIP missing {name}")
        return

    stem = src.stem
    webp = ROOT / f"{stem}.webp"
    before = src.stat().st_size

    img = Image.open(src)
    has_alpha = img.mode in {"RGBA", "LA"} or "transparency" in img.info
    if name.startswith("bg-generation"):
        img = resize_max(img.convert("RGB"), max_side)
        save_webp(img, webp, quality)
        jpg = ROOT / f"{stem}.jpg"
        img.save(jpg, format="JPEG", quality=BG_JPEG_QUALITY, optimize=True, progressive=True)
        print(f"{stem}: PNG {before // 1024}KB -> webp {webp.stat().st_size // 1024}KB, jpg {jpg.stat().st_size // 1024}KB")
    else:
        if has_alpha:
            img = resize_max(img.convert("RGBA"), max_side)
        else:
            img = resize_max(img.convert("RGB"), max_side)
        save_webp(img, webp, quality)
        print(f"{stem}: PNG {before // 1024}KB -> webp {webp.stat().st_size // 1024}KB {img.size}")
        src.unlink()


def main() -> None:
    if not ROOT.is_dir():
        raise SystemExit(f"Missing {ROOT}")

    for name, max_side, quality in ASSETS:
        compress_one(name, max_side, quality)

    if (ROOT / "bg-generation.png").is_file():
        (ROOT / "bg-generation.png").unlink()

    total = sum(p.stat().st_size for p in ROOT.iterdir() if p.is_file())
    print(f"total assets: {total // 1024} KB")


if __name__ == "__main__":
    main()
