#!/usr/bin/env python3
"""Коллизии стен + точные позиции объектов из Figma (game.txt)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "assets" / "figma" / "_context" / "game.txt"
OUT_JSON = ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json"

from maze_constants import COLS, FIELD_H, FIELD_W, OX, OY, ROWS, TILE, TILE_H, TILE_W
WALL_THRESHOLD = 0.58

WALL_VARS = {"img1020", "img5619343", "img793938", "img14189"}

FIGMA_ENTITIES = [
    {"id": "25:172", "role": "player", "cx": 438.5, "cy": 374.16},
    {"id": "25:141", "role": "ghost", "ghostId": "fomo", "cx": 262.99, "cy": 195.06},
    {"id": "25:163", "role": "ghost", "ghostId": "inflation", "cx": 407.0, "cy": 198.0},
    {"id": "25:151", "role": "ghost", "ghostId": "impulse", "cx": 235.29, "cy": 429.29},
    {"id": "25:197", "role": "portfolio", "cx": 179.0, "cy": 374.0},
]

FIGMA_PELLETS = [
    {"cx": 440.0, "cy": 430.0, "type": "coin"},
    {"cx": 411.0, "cy": 430.0, "type": "coin"},
    {"cx": 383.0, "cy": 430.0, "type": "coin"},
    {"cx": 351.0, "cy": 430.0, "type": "coin"},
    {"cx": 322.0, "cy": 430.0, "type": "coin"},
    {"cx": 440.0, "cy": 402.0, "type": "coin"},
    {"cx": 291.0, "cy": 432.0, "type": "percent"},
    {"cx": 351.0, "cy": 405.0, "type": "logo"},
]


def parse_box(classes: str) -> dict:
    left = top = w = h = None
    for token in classes.split():
        if token.startswith("left-[") and "calc" not in token:
            m = re.search(r"left-\[([\d.]+)px\]", token)
            if m:
                left = float(m.group(1))
        elif token.startswith("top-[") and "calc" not in token:
            m = re.search(r"top-\[([\d.]+)px\]", token)
            if m:
                top = float(m.group(1))
        elif token.startswith("w-["):
            m = re.search(r"w-\[([\d.]+)px\]", token)
            if m:
                w = float(m.group(1))
        elif token.startswith("h-["):
            m = re.search(r"h-\[([\d.]+)px\]", token)
            if m:
                h = float(m.group(1))
        elif token.startswith("size-["):
            m = re.search(r"size-\[([\d.]+)px\]", token)
            if s := (float(m.group(1)) if m else None):
                w = h = s
    return {"left": left, "top": top, "w": w, "h": h}


def parse_walls(text: str) -> list[tuple[float, float, float, float]]:
    lines = text.splitlines()
    stack: list[dict] = []
    walls: list[tuple[float, float, float, float]] = []
    for line in lines:
        if "<div" in line:
            cm = re.search(r'className="([^"]*)"', line)
            stack.append(parse_box(cm.group(1) if cm else ""))
        if "src={" in line:
            sm = re.search(r"src=\{(\w+)\}", line)
            if sm and sm.group(1) in WALL_VARS:
                abs_l = abs_t = None
                bw = bh = None
                for s in stack:
                    if s["left"] is not None:
                        abs_l = s["left"]
                    if s["top"] is not None:
                        abs_t = s["top"]
                    if s["w"] is not None:
                        bw = s["w"]
                    if s["h"] is not None:
                        bh = s["h"]
                if abs_l is not None and abs_t is not None and bw and bh:
                    walls.append((abs_l, abs_t, bw, bh))
        if "</div>" in line and stack:
            stack.pop()
    return walls


def overlap_ratio(left: float, top: float, w: float, h: float, gx: int, gy: int) -> float:
    x0 = OX + gx * TILE_W
    y0 = OY + gy * TILE_H
    ix0 = max(x0, left)
    iy0 = max(y0, top)
    ix1 = min(x0 + TILE_W, left + w)
    iy1 = min(y0 + TILE_H, top + h)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0) / (TILE_W * TILE_H)


def is_wall(walls: list, gx: int, gy: int) -> bool:
    return max((overlap_ratio(l, t, w, h, gx, gy) for l, t, w, h in walls), default=0.0) >= WALL_THRESHOLD


def world_to_grid(cx: float, cy: float) -> tuple[int, int]:
    return (
        max(0, min(COLS - 1, round((cx - OX - TILE_W / 2) / TILE_W))),
        max(0, min(ROWS - 1, round((cy - OY - TILE_H / 2) / TILE_H))),
    )


def nearest_open(grid: list[list[str]], gx: int, gy: int) -> tuple[int, int]:
    if grid[gy][gx] != "#":
        return gx, gy
    for r in range(1, 5):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS and grid[ny][nx] != "#":
                    return nx, ny
    return gx, gy


def main() -> None:
    walls = parse_walls(SRC.read_text(encoding="utf-8", errors="replace"))
    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for gy in range(ROWS):
        for gx in range(COLS):
            if is_wall(walls, gx, gy):
                grid[gy][gx] = "#"

    for x in range(COLS):
        grid[0][x] = "#"
        grid[ROWS - 1][x] = "#"
    for y in range(ROWS):
        grid[y][0] = "#"
        grid[y][COLS - 1] = "#"

    rows = ["".join(r) for r in grid]

    player_start = None
    ghost_spawns = []
    portfolio_tile = None

    for ent in FIGMA_ENTITIES:
        gx, gy = world_to_grid(ent["cx"], ent["cy"])
        gx, gy = nearest_open(grid, gx, gy)
        if ent["role"] == "player":
            player_start = {"x": gx, "y": gy, "wx": ent["cx"], "wy": ent["cy"]}
        elif ent["role"] == "ghost":
            ghost_spawns.append({
                "id": ent["ghostId"],
                "x": gx,
                "y": gy,
                "wx": ent["cx"],
                "wy": ent["cy"],
            })
        elif ent["role"] == "portfolio":
            portfolio_tile = {"x": gx, "y": gy, "wx": ent["cx"], "wy": ent["cy"]}

    pellets = []
    for i, p in enumerate(FIGMA_PELLETS):
        pellets.append({
            "id": f"p{i}",
            "type": p["type"],
            "wx": p["cx"],
            "wy": p["cy"],
            "points": 25 if p["type"] == "percent" else 50 if p["type"] == "logo" else 10,
        })

    out = {
        "fieldOrigin": [OX, OY],
        "fieldSize": [FIELD_W, FIELD_H],
        "tileW": TILE_W,
        "tileH": TILE_H,
        "tile": TILE,
        "cols": COLS,
        "rows": ROWS,
        "wallsFound": len(walls),
        "rows_ascii": rows,
        "playerStart": player_start,
        "ghostSpawns": ghost_spawns,
        "portfolioTile": portfolio_tile,
        "pellets": pellets,
    }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"walls={len(walls)} walkable={sum(r.count('.') for r in rows)} pellets={len(pellets)}")
    print("player", player_start)
    print("ghosts", ghost_spawns)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
