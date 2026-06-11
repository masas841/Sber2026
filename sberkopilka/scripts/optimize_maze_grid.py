#!/usr/bin/env python3
"""Сетка лабиринта: стены Figma + принудительные коридоры у объектов + связность."""
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

MARKERS = [
    (e["cx"], e["cy"])
    for e in bf.FIGMA_ENTITIES
] + [(p["cx"], p["cy"]) for p in bf.FIGMA_PELLETS]


def cell_center(gx: int, gy: int) -> tuple[float, float]:
    return OX + gx * TILE + TILE / 2, OY + gy * TILE + TILE / 2


def world_to_grid(cx: float, cy: float) -> tuple[int, int]:
    return (
        max(0, min(COLS - 1, int((cx - OX) / TILE))),
        max(0, min(ROWS - 1, int((cy - OY) / TILE))),
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


def cell_overlap(walls: list, gx: int, gy: int) -> float:
    return max((bf.overlap_ratio(l, t, w, h, gx, gy) for l, t, w, h in walls), default=0.0)


def carve_path(grid: list[list[str]], walls: list, ax: int, ay: int, bx: int, by: int, cap: float) -> None:
    """A* по клеткам с overlap < cap — соединяет маркеры с игроком."""
    import heapq

    def h(x: int, y: int) -> int:
        return abs(x - bx) + abs(y - by)

    open_set: list[tuple[int, int, int]] = [(h(ax, ay), 0, ax, ay)]
    came: dict[tuple[int, int], tuple[int, int] | None] = {(ax, ay): None}
    g_score = {(ax, ay): 0}

    while open_set:
        _, g, x, y = heapq.heappop(open_set)
        if (x, y) == (bx, by):
            cur = (bx, by)
            while cur is not None:
                cx, cy = cur
                grid[cy][cx] = "."
                cur = came[cur]
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 < nx < COLS - 1 and 0 < ny < ROWS - 1):
                continue
            if cell_overlap(walls, nx, ny) >= cap:
                continue
            ng = g + 1
            if ng < g_score.get((nx, ny), 1e9):
                g_score[(nx, ny)] = ng
                came[(nx, ny)] = (x, y)
                heapq.heappush(open_set, (ng + h(nx, ny), ng, nx, ny))


def build_grid(walls: list, threshold: float, player: tuple[int, int]) -> list[list[str]]:
    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for gy in range(ROWS):
        for gx in range(COLS):
            if cell_overlap(walls, gx, gy) >= threshold:
                grid[gy][gx] = "#"
    for cx, cy in MARKERS:
        gx, gy = world_to_grid(cx, cy)
        grid[gy][gx] = "."
        carve_path(grid, walls, gx, gy, player[0], player[1], 0.99)
    for x in range(COLS):
        grid[0][x] = grid[ROWS - 1][x] = "#"
    for y in range(ROWS):
        grid[y][0] = grid[y][COLS - 1] = "#"
    return grid


def nearest_in_reach(reach: set[tuple[int, int]], cx: float, cy: float) -> tuple[int, int]:
    best = None
    best_d = 1e9
    for gx, gy in reach:
        wx, wy = cell_center(gx, gy)
        d = (wx - cx) ** 2 + (wy - cy) ** 2
        if d < best_d:
            best_d = d
            best = (gx, gy)
    return best or (0, 0)


def main() -> None:
    walls = bf.parse_walls(bf.SRC.read_text(encoding="utf-8", errors="replace"))
    player_figma = next(e for e in bf.FIGMA_ENTITIES if e["role"] == "player")
    pgx, pgy = world_to_grid(player_figma["cx"], player_figma["cy"])

    best = None
    for th in [x / 100 for x in range(50, 66, 2)]:
        grid = build_grid(walls, th, (pgx, pgy))
        reach0 = flood(grid, pgx, pgy)
        if len(reach0) < 12:
            continue
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] == "." and (x, y) not in reach0:
                    grid[y][x] = "#"
        reach = flood(grid, pgx, pgy)
        markers_hit = sum(
            1 for cx, cy in MARKERS if nearest_in_reach(reach, cx, cy) == world_to_grid(cx, cy)
        )
        score = len(reach) * 10 + markers_hit
        if best is None or score > best[0]:
            best = (score, th, grid, reach)

    _, th, grid, reach = best
    rows = ["".join(r) for r in grid]

    entities: dict = {}
    ghosts = []
    used: set[tuple[int, int]] = set()
    for ent in bf.FIGMA_ENTITIES:
        gx, gy = world_to_grid(ent["cx"], ent["cy"])
        if (gx, gy) not in reach:
            gx, gy = nearest_in_reach(reach, ent["cx"], ent["cy"])
        if ent["role"] != "player" and (gx, gy) in used:
            alt = sorted(
                reach,
                key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2
                + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2,
            )
            for c in alt:
                if c not in used:
                    gx, gy = c
                    break
        if ent["role"] != "player":
            used.add((gx, gy))
        item = {"x": gx, "y": gy, "wx": round(ent["cx"], 2), "wy": round(ent["cy"], 2)}
        if ent["role"] == "player":
            entities["playerStart"] = item
        elif ent["role"] == "ghost":
            item["id"] = ent["ghostId"]
            ghosts.append(item)
        elif ent["role"] == "portfolio":
            entities["portfolioTile"] = item

    out = {
        "fieldOrigin": [OX, OY],
        "tile": TILE,
        "cols": COLS,
        "rows": ROWS,
        "wallThreshold": th,
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

    print(f"threshold={th:.2f} reachable={len(reach)}")
    print("player", entities["playerStart"])
    print("ghosts", ghosts)
    print("portfolio", entities.get("portfolioTile"))
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
