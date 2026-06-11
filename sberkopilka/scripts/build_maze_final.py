#!/usr/bin/env python3
"""Финальная сетка: стены Figma (overlap) + открытые клетки маркеров + связность."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import build_maze_from_figma as bf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json"
OUT_JS = ROOT / "web" / "js" / "maze-layout.generated.json"

OX, OY, TILE = bf.OX, bf.OY, bf.TILE
COLS, ROWS = bf.COLS, bf.ROWS
WALL_TH = 0.58


def cell_center(gx: int, gy: int) -> tuple[float, float]:
    return OX + gx * TILE + TILE / 2, OY + gy * TILE + TILE / 2


def world_to_grid(cx: float, cy: float) -> tuple[int, int]:
    return (
        max(0, min(COLS - 1, round((cx - OX - TILE / 2) / TILE))),
        max(0, min(ROWS - 1, round((cy - OY - TILE / 2) / TILE))),
    )


def flood(grid: list[list[str]], sx: int, sy: int) -> set[tuple[int, int]]:
    if grid[sy][sx] == "#":
        return set()
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and grid[ny][nx] != "#" and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def marker_cells() -> set[tuple[int, int]]:
    cells = set()
    for e in bf.FIGMA_ENTITIES:
        gx, gy = world_to_grid(e["cx"], e["cy"])
        cells.add((gx, gy))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = gx + dx, gy + dy
            if 0 < nx < COLS - 1 and 0 < ny < ROWS - 1:
                cells.add((nx, ny))
    for p in bf.FIGMA_PELLETS:
        gx, gy = world_to_grid(p["cx"], p["cy"])
        cells.add((gx, gy))
    return cells


def main() -> None:
    walls = bf.parse_walls(bf.SRC.read_text(encoding="utf-8", errors="replace"))
    markers = marker_cells()
    player = next(e for e in bf.FIGMA_ENTITIES if e["role"] == "player")
    pgx, pgy = world_to_grid(player["cx"], player["cy"])

    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for gy in range(ROWS):
        for gx in range(COLS):
            ov = max((bf.overlap_ratio(l, t, w, h, gx, gy) for l, t, w, h in walls), default=0.0)
            if ov >= WALL_TH and (gx, gy) not in markers:
                grid[gy][gx] = "#"

    # убрать ложные углы (вне визуального лабиринта)
    for y in (1, 2):
        for x in range(COLS):
            if x < 4 or x > COLS - 5:
                grid[y][x] = "#"

    for x in range(COLS):
        grid[0][x] = grid[ROWS - 1][x] = "#"
    for y in range(ROWS):
        grid[y][0] = grid[y][COLS - 1] = "#"

    reach = flood(grid, pgx, pgy)
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x] == "." and (x, y) not in reach:
                grid[y][x] = "#"
    reach = flood(grid, pgx, pgy)

    rows = ["".join(r) for r in grid]

    def snap_entity(ent: dict) -> dict:
        gx, gy = world_to_grid(ent["cx"], ent["cy"])
        if (gx, gy) not in reach:
            gx, gy = min(reach, key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2 + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2)
        return {"x": gx, "y": gy, "wx": round(ent["cx"], 2), "wy": round(ent["cy"], 2)}

    entities = {"playerStart": snap_entity(player)}
    ghosts = []
    used = {world_to_grid(player["cx"], player["cy"])}
    for ent in bf.FIGMA_ENTITIES:
        if ent["role"] == "ghost":
            item = snap_entity(ent)
            k = (item["x"], item["y"])
            if k in used:
                for c in sorted(reach, key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2 + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2):
                    if c not in used:
                        item["x"], item["y"] = c
                        break
            used.add((item["x"], item["y"]))
            ghosts.append(item)
        elif ent["role"] == "portfolio":
            entities["portfolioTile"] = snap_entity(ent)

    out = {
        "fieldOrigin": [OX, OY],
        "tile": TILE,
        "cols": COLS,
        "rows": ROWS,
        "wallThreshold": WALL_TH,
        "source": "figma-overlap+markers",
        "rows_ascii": rows,
        "playerStart": entities["playerStart"],
        "ghostSpawns": ghosts,
        "portfolioTile": entities.get("portfolioTile"),
        "reachableCount": len(reach),
        "reachable": [[x, y] for x, y in sorted(reach)],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JS.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"reachable={len(reach)} walkable={sum(r.count('.') for r in rows)}")
    print("player", entities["playerStart"])
    print("ghosts", ghosts)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
