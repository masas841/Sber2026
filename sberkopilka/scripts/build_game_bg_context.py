#!/usr/bin/env python3
"""game-bg.txt — фон Figma: декор, тени, стены, HUD. Без героев/пеллетов/портфеля."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "assets" / "figma" / "_context" / "game.txt"
OUT = ROOT / "web" / "assets" / "figma" / "_context" / "game-bg.txt"


def main() -> None:
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()
    field_end = next(i for i, ln in enumerate(lines) if 'data-name="Герои"' in ln)
    tail_start = next(i for i, ln in enumerate(lines) if 'data-name="Счет"' in ln)
    tail_end = next(i for i, ln in enumerate(lines) if 'data-name="Штуки на поле"' in ln)
    border = next(ln for ln in lines if 'data-name="Границы экрана"' in ln)

    body = lines[:field_end] + lines[tail_start:tail_end] + [border, "    </div>", "  );", "}"]

    raw = "\n".join(body)
    raw = re.sub(
        r"export default function Game\(\)",
        "export default function GameBg()",
        raw,
        count=1,
    )
    OUT.write_text(raw + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(body)} lines")


if __name__ == "__main__":
    main()
