#!/usr/bin/env python3
"""Добавляет строки вниз к maze-layout (15 → 23)."""
from __future__ import annotations

import json
from pathlib import Path

from maze_constants import COLS, ROWS

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / "web" / "js" / "maze-layout.generated.json",
    ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json",
]
WALL_ROW = "#" * COLS


def pad_rows(rows: list[str]) -> list[str]:
    if len(rows) >= ROWS:
        return rows[:ROWS]
    if not rows:
        return [WALL_ROW] * ROWS
    # без дублирования старой нижней рамки — добавляем пустые строки-стены
    body = rows[:-1] if len(rows) >= 15 and rows[-1] == WALL_ROW else rows
    need = ROWS - len(body)
    if need <= 0:
        return body[:ROWS]
    extra = [WALL_ROW] * (need - 1) + [WALL_ROW]
    return body + extra


def main() -> None:
    for path in PATHS:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"] = ROWS
        data["cols"] = COLS
        data["rows_ascii"] = pad_rows(data.get("rows_ascii", []))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{path.name}: {len(data['rows_ascii'])} rows")


if __name__ == "__main__":
    main()
