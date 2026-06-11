#!/usr/bin/env python3
"""Копирует maze-layout.generated.json → web/js/maze.js"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "js" / "maze-layout.generated.json"
OUT = ROOT / "web" / "js" / "maze.js"

from maze_constants import FIELD_H, FIELD_W, TILE, TILE_H, TILE_W

def cell_world(ox: float, oy: float, tw: float, th: float, gx: int, gy: int) -> tuple[float, float]:
    return round(ox + gx * tw + tw / 2, 2), round(oy + gy * th + th / 2, 2)


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = data["rows_ascii"]
    ox, oy = data["fieldOrigin"]
    field_w, field_h = data.get("fieldSize", [FIELD_W, FIELD_H])
    tile_w = data.get("tileW", field_w / data.get("cols", 16))
    tile_h = data.get("tileH", field_h / data.get("rows", 17))
    tile = data.get("tile", (tile_w + tile_h) / 2)
    ps = data["playerStart"]
    ghosts = data["ghostSpawns"]
    pf = data.get("portfolioTile")

    ps_wx, ps_wy = cell_world(ox, oy, tile_w, tile_h, ps["x"], ps["y"])
    ghosts_norm = []
    for g in ghosts:
        gwx, gwy = cell_world(ox, oy, tile_w, tile_h, g["x"], g["y"])
        ghosts_norm.append({**g, "wx": gwx, "wy": gwy})
    pf_wx = pf_wy = None
    if pf:
        pf_wx, pf_wy = cell_world(ox, oy, tile_w, tile_h, pf["x"], pf["y"])

    ghosts_js = ",\n    ".join(
        (
            f"{{ id: \"{g['id']}\", x: {g['x']}, y: {g['y']}, wx: {g['wx']}, wy: {g['wy']} }}"
            if g.get("id")
            else f"{{ x: {g['x']}, y: {g['y']}, wx: {g['wx']}, wy: {g['wy']} }}"
        )
        for g in ghosts_norm
    )
    rows_js = ",\n  ".join(f'"{r}"' for r in rows)
    pellets_js = ""

    content = f"""/** Лабиринт 16×17 — автоген: scripts/optimize_maze_grid.py + sync_maze_to_js.py */

const SCREEN_W = 672;
const SCREEN_H = 672;

const FIGMA_FIELD = {{
  x: {ox},
  y: {oy},
  width: {field_w},
  height: {field_h},
  tileW: {tile_w},
  tileH: {tile_h},
}};
const TILE_W = FIGMA_FIELD.tileW;
const TILE_H = FIGMA_FIELD.tileH;
const TILE = ({tile_w} + {tile_h}) / 2;

const MAZE_ROWS = [
  {rows_js},
];

const FIGMA_ENTITIES = {{
  playerStart: {{ x: {ps['x']}, y: {ps['y']}, wx: {ps_wx}, wy: {ps_wy} }},
  ghostSpawns: [
    {ghosts_js},
  ],
  portfolioTile: {f"{{ x: {pf['x']}, y: {pf['y']}, wx: {pf_wx}, wy: {pf_wy} }}" if pf else "null"},
}};

/** Демо-монеты отключены — позиции только из сетки (cellWorld) */
const FIGMA_DEMO_PELLETS = [
  {pellets_js}
];

const PELLET_WEIGHTS = {{ coin: 0.82, percent: 0.11, logo: 0.07 }};

const SCORE_COIN = 10;
const SCORE_PERCENT = 25;
const SCORE_LOGO = 50;
const PORTFOLIO_DURATION_MS = 8000;

function cellWorld(gx, gy) {{
  return {{
    wx: FIGMA_FIELD.x + gx * TILE_W + TILE_W / 2,
    wy: FIGMA_FIELD.y + gy * TILE_H + TILE_H / 2,
  }};
}}

function floodReachable(rows, sx, sy) {{
  const cols = rows[0].length;
  const seen = new Set();
  const key = (x, y) => `${{x}},${{y}}`;
  if (rows[sy][sx] === "#") return seen;
  const q = [[sx, sy]];
  seen.add(key(sx, sy));
  while (q.length) {{
    const [x, y] = q.shift();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {{
      const nx = x + dx;
      const ny = y + dy;
      const k = key(nx, ny);
      if (nx < 0 || ny < 0 || nx >= cols || ny >= rows.length) continue;
      if (rows[ny][nx] === "#" || seen.has(k)) continue;
      seen.add(k);
      q.push([nx, ny]);
    }}
  }}
  return seen;
}}

const REACHABLE = floodReachable(MAZE_ROWS, FIGMA_ENTITIES.playerStart.x, FIGMA_ENTITIES.playerStart.y);

function worldToGrid(wx, wy) {{
  return {{
    x: Math.max(0, Math.min(MAZE_ROWS[0].length - 1, Math.round((wx - FIGMA_FIELD.x - TILE_W / 2) / TILE_W))),
    y: Math.max(0, Math.min(MAZE_ROWS.length - 1, Math.round((wy - FIGMA_FIELD.y - TILE_H / 2) / TILE_H))),
  }};
}}

function reservedCells() {{
  const set = new Set();
  const mark = (x, y) => set.add(`${{x}},${{y}}`);
  mark(FIGMA_ENTITIES.playerStart.x, FIGMA_ENTITIES.playerStart.y);
  FIGMA_ENTITIES.ghostSpawns.forEach((g) => mark(g.x, g.y));
  if (FIGMA_ENTITIES.portfolioTile) mark(FIGMA_ENTITIES.portfolioTile.x, FIGMA_ENTITIES.portfolioTile.y);
  return set;
}}

function pickPelletType() {{
  const r = Math.random();
  if (r < PELLET_WEIGHTS.coin) return "coin";
  if (r < PELLET_WEIGHTS.coin + PELLET_WEIGHTS.percent) return "percent";
  return "logo";
}}

function generateRandomPellets() {{
  const reserved = reservedCells();
  const pellets = [];
  let n = 0;

  for (let y = 0; y < MAZE_ROWS.length; y++) {{
    for (let x = 0; x < MAZE_ROWS[y].length; x++) {{
      const k = `${{x}},${{y}}`;
      if (MAZE_ROWS[y][x] === "#") continue;
      if (!REACHABLE.has(k)) continue;
      if (reserved.has(k)) continue;

      const type = pickPelletType();
      const w = cellWorld(x, y);
      pellets.push({{
        id: `r${{n++}}`,
        type,
        x,
        y,
        wx: w.wx,
        wy: w.wy,
        points: type === "percent" ? SCORE_PERCENT : type === "logo" ? SCORE_LOGO : SCORE_COIN,
      }});
    }}
  }}
  return pellets;
}}

function parseMaze() {{
  const walls = [];
  for (let y = 0; y < MAZE_ROWS.length; y++) {{
    for (let x = 0; x < MAZE_ROWS[y].length; x++) {{
      const k = `${{x}},${{y}}`;
      if (MAZE_ROWS[y][x] === "#" || !REACHABLE.has(k)) walls.push({{ x, y }});
    }}
  }}

  return {{
    cols: MAZE_ROWS[0].length,
    rows: MAZE_ROWS.length,
    walls,
    pellets: generateRandomPellets(),
    playerStart: {{ ...FIGMA_ENTITIES.playerStart }},
    portfolioTile: {{ ...FIGMA_ENTITIES.portfolioTile }},
    ghostSpawns: FIGMA_ENTITIES.ghostSpawns.map((g) => ({{ ...g }})),
  }};
}}

const MAZE = parseMaze();

window.KopilkaMaze = {{
  SCREEN_W,
  SCREEN_H,
  TILE,
  TILE_W,
  TILE_H,
  FIGMA_FIELD,
  FIGMA_ENTITIES,
  FIGMA_DEMO_PELLETS,
  PELLET_WEIGHTS,
  MAZE,
  MAZE_ROWS,
  REACHABLE,
  generateRandomPellets,
  cellWorld,
  worldToGrid,
  SCORE_COIN,
  SCORE_PERCENT,
  SCORE_LOGO,
  PORTFOLIO_DURATION_MS,
}};
"""
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
