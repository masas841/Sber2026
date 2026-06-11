#!/usr/bin/env python3
"""Сетка лабиринта из PNG-тени поля (чёрное = коридор, бирюза = стена)."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

import build_maze_from_figma as bf

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "scripts" / "_cache"
OUT = ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json"
OUT_JS = ROOT / "web" / "js" / "maze-layout.generated.json"
DEBUG = CACHE / "maze-debug.png"

OX, OY, TILE = bf.OX, bf.OY, bf.TILE
COLS, ROWS = bf.COLS, bf.ROWS
SCREEN = 672
# Центр тени в макете 672×672
SHADOW_CX, SHADOW_CY = 336, 347


def load_shadow_gray() -> Image.Image:
    img = Image.open(CACHE / "shadow1.png").convert("RGBA")
    layer = Image.new("RGBA", (SCREEN, SCREEN), (0, 0, 0, 0))
    layer.paste(img, (int(SHADOW_CX - img.width / 2), int(SHADOW_CY - img.height / 2)), img)
    rgb = Image.new("RGB", (SCREEN, SCREEN), (0, 0, 0))
    rgb.paste(layer, mask=layer.split()[3])
    return rgb.convert("L")


def is_corridor(gray: Image.Image, wx: float, wy: float) -> bool:
    x = int(round(wx))
    y = int(round(wy))
    if not (0 <= x < SCREEN and 0 <= y < SCREEN):
        return False
    # чёрный фон тени = проход; бирюзовые линии = стена (светлее)
    return gray.getpixel((x, y)) < 48


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


def marker_score(reach: set[tuple[int, int]]) -> int:
    s = 0
    for e in bf.FIGMA_ENTITIES:
        if world_to_grid(e["cx"], e["cy"]) in reach:
            s += 3
    for p in bf.FIGMA_PELLETS:
        if world_to_grid(p["cx"], p["cy"]) in reach:
            s += 1
    return s


def main() -> None:
    gray = load_shadow_gray()
    player = next(e for e in bf.FIGMA_ENTITIES if e["role"] == "player")
    pgx, pgy = world_to_grid(player["cx"], player["cy"])

    best = None
    for th in range(30, 80, 4):
        grid = [["." if is_corridor(gray, *cell_center(gx, gy)) and gray.getpixel((int(cell_center(gx, gy)[0]), int(cell_center(gx, gy)[1]))) < th else "#"
                 for gx in range(COLS)] for gy in range(ROWS)]
        # на самом деле is_corridor уже использует th — пересоберём чище
        grid = []
        for gy in range(ROWS):
            row = []
            for gx in range(COLS):
                wx, wy = cell_center(gx, gy)
                xi, yi = int(wx), int(wy)
                lum = gray.getpixel((xi, yi)) if 0 <= xi < SCREEN and 0 <= yi < SCREEN else 255
                row.append("." if lum < th else "#")
            grid.append(row)

        for x in range(COLS):
            grid[0][x] = grid[ROWS - 1][x] = "#"
        for y in range(ROWS):
            grid[y][0] = grid[y][COLS - 1] = "#"

        reach = flood(grid, pgx, pgy)
        if len(reach) < 20:
            continue
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] == "." and (x, y) not in reach:
                    grid[y][x] = "#"
        reach = flood(grid, pgx, pgy)
        ms = marker_score(reach)
        sc = ms * 30 + len(reach)
        if best is None or sc > best[0]:
            best = (sc, th, grid, reach)

    _, th, grid, reach = best
    rows = ["".join(r) for r in grid]

    # debug
    dbg = Image.new("RGB", (SCREEN, SCREEN), (20, 20, 20))
    dr = ImageDraw.Draw(dbg)
    dbg.paste(gray.convert("RGB"), (0, 0))
    for gy in range(ROWS):
        for gx in range(COLS):
            wx, wy = cell_center(gx, gy)
            color = (0, 220, 80) if grid[gy][gx] == "." else (220, 40, 40)
            dr.rectangle([wx - TILE / 2, wy - TILE / 2, wx + TILE / 2, wy + TILE / 2], outline=color, width=1)
    dbg.save(DEBUG)

    def snap(ent: dict) -> dict:
        gx, gy = world_to_grid(ent["cx"], ent["cy"])
        if (gx, gy) not in reach:
            gx, gy = min(reach, key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2 + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2)
        return {"x": gx, "y": gy, "wx": round(ent["cx"], 2), "wy": round(ent["cy"], 2)}

    entities = {"playerStart": snap(player)}
    ghosts, used = [], set()
    for ent in bf.FIGMA_ENTITIES:
        if ent["role"] == "ghost":
            item = snap(ent)
            k = (item["x"], item["y"])
            if k in used:
                for c in sorted(reach, key=lambda c: (ent["cx"] - cell_center(c[0], c[1])[0]) ** 2 + (ent["cy"] - cell_center(c[0], c[1])[1]) ** 2):
                    if c not in used:
                        item["x"], item["y"] = c
                        break
            used.add((item["x"], item["y"]))
            ghosts.append(item)
        elif ent["role"] == "portfolio":
            entities["portfolioTile"] = snap(ent)

    out = {
        "fieldOrigin": [OX, OY],
        "tile": TILE,
        "cols": COLS,
        "rows": ROWS,
        "source": "shadow1-path",
        "lumThreshold": th,
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

    print(f"lum_th={th} reachable={len(reach)} markers={marker_score(reach)}")
    print("player", entities["playerStart"])
    print("ghosts", ghosts)
    for row in rows:
        print(row)
    print("debug", DEBUG)


if __name__ == "__main__":
    main()
