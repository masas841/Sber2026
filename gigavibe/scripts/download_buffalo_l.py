"""Скачать buffalo_l для InsightFace (профиль гостя / smile detection)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.generators.ref_video import _ensure_buffalo_l, INSIGHTFACE_ROOT


def main() -> int:
    _ensure_buffalo_l()
    marker = INSIGHTFACE_ROOT / "models" / "buffalo_l" / "w600k_r50.onnx"
    print(f"buffalo_l OK: {marker}")
    return 0 if marker.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
