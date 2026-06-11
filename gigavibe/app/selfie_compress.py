"""Сжатие селфи для API: VPN/Clash часто режет upload >~20 КБ."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

# Под лимит ~20 КБ на upload через TUN/прокси (см. smoke tmpfiles).
MAX_SELFIE_UPLOAD_BYTES = 18_000
MAX_SELFIE_UPLOAD_SIDE = 480


def compress_selfie_jpeg(
    path: Path,
    *,
    max_bytes: int = MAX_SELFIE_UPLOAD_BYTES,
    max_side: int = MAX_SELFIE_UPLOAD_SIDE,
) -> bytes:
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    quality = 82
    buf = io.BytesIO()
    for _ in range(8):
        buf.seek(0)
        buf.truncate(0)
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes or quality <= 40:
            break
        quality -= 5
    return buf.getvalue()
