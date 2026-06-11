#!/usr/bin/env python3
"""Приводит maze-layout к COLS×ROWS из maze_constants."""
from __future__ import annotations

import json
from pathlib import Path

import build_maze_from_figma as bf
from maze_constants import COLS, FIELD_H, FIELD_W, OX, OY, ROWS, TILE, TILE_H, TILE_W

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / "web" / "js" / "maze-layout.generated.json",
    ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json",
]
WALL = "#" * COLS


def world_to_grid(cx: float, cy: float) -> tuple[int, int]:
    return (
        max(0, min(COLS - 1, round((cx - OX - TILE_W / 2) / TILE_W))),
        max(0, min(ROWS - 1, round((cy - OY - TILE_H / 2) / TILE_H))),
    )


def crop_rows(rows: list[str]) -> list[str]:
    out: list[str] = []
    for y in range(ROWS):
        if y < len(rows):
            line = rows[y]
            if len(line) >= COLS:
                out.append(line[:COLS])
            else:
                out.append(line.ljust(COLS, "#")[:COLS])
        else:
            out.append(WALL)
    # рамка
    for x in range(COLS):
        out[0] = WALL
        out[ROWS - 1] = WALL
    for y in range(ROWS):
        chars = list(out[y])
        chars[0] = chars[COLS - 1] = "#"
        out[y] = "".join(chars)
    return out


def cell_center(gx: int, gy: int) -> tuple[float, float]:
    return OX + gx * TILE_W + TILE_W / 2, OY + gy * TILE_H + TILE_H / 2


def nearest_open(rows: list[str], cx: float, cy: float) -> tuple[int, int]:
    gx, gy = world_to_grid(cx, cy)
    if rows[gy][gx] != "#":
        return gx, gy
    best = (gx, gy)
    best_d = float("inf")
    for y in range(ROWS):
        for x in range(COLS):
            if rows[y][x] == "#":
                continue
            wx, wy = cell_center(x, y)
            d = (cx - wx) ** 2 + (cy - wy) ** 2
            if d < best_d:
                best_d = d
                best = (x, y)
    return best


def flood(rows: list[str], sx: int, sy: int) -> set[tuple[int, int]]:
    if rows[sy][sx] == "#":
        return set()
    from collections import deque

    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and rows[ny][nx] != "#" and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def snap_entities_on_rows(rows: list[str], reach: set[tuple[int, int]], cx: float, cy: float) -> tuple[int, int]:
    gx, gy = world_to_grid(cx, cy)
    if rows[gy][gx] != "#" and (not reach or (gx, gy) in reach):
        return gx, gy
    pool = reach if reach else {
        (x, y) for y in range(ROWS) for x in range(COLS) if rows[y][x] != "#"
    }
    if not pool:
        return gx, gy
    return min(
        pool,
        key=lambda c: (cx - cell_center(c[0], c[1])[0]) ** 2
        + (cy - cell_center(c[0], c[1])[1]) ** 2,
    )


def main() -> None:
    player = next(e for e in bf.FIGMA_ENTITIES if e["role"] == "player")

    for path in PATHS:
        if not path.exists():
            data = {"rows_ascii": [WALL] * ROWS}
        else:
            data = json.loads(path.read_text(encoding="utf-8"))

        rows = crop_rows(data.get("rows_ascii", []))
        pgx, pgy = nearest_open(rows, player["cx"], player["cy"])
        reach = flood(rows, pgx, pgy)

        ghosts = []
        used: set[tuple[int, int]] = set()
        portfolio = None
        for ent in bf.FIGMA_ENTITIES:
            gx, gy = snap_entities_on_rows(rows, reach, ent["cx"], ent["cy"])
            item = {"x": gx, "y": gy, "wx": round(ent["cx"], 2), "wy": round(ent["cy"], 2)}
            if ent["role"] == "player":
                player_start = item
            elif ent["role"] == "ghost":
                if (gx, gy) in used:
                    for c in sorted(
                        reach,
                        key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2
                        + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2,
                    ):
                        if c not in used:
                            gx, gy = c
                            item["x"], item["y"] = gx, gy
                            break
                used.add((gx, gy))
                ghosts.append(item)
            elif ent["role"] == "portfolio":
                portfolio = item

        out = {
            "fieldOrigin": [OX, OY],
            "fieldSize": [FIELD_W, FIELD_H],
            "tileW": TILE_W,
            "tileH": TILE_H,
            "tile": TILE,
            "cols": COLS,
            "rows": ROWS,
            "source": "resize-16x17",
            "rows_ascii": rows,
            "playerStart": player_start,
            "ghostSpawns": ghosts,
            "portfolioTile": portfolio,
            "reachableCount": len(reach),
            "reachable": [[x, y] for x, y in sorted(reach)],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{path.name}: {COLS}x{ROWS} reachable={len(reach)}")


if __name__ == "__main__":
    main()
