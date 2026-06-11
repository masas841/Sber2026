/** Лабиринт 16×17 — автоген: scripts/optimize_maze_grid.py + sync_maze_to_js.py */

const SCREEN_W = 672;
const SCREEN_H = 672;

const FIGMA_FIELD = {
  x: 100,
  y: 100,
  width: 473,
  height: 492,
  tileW: 29.5625,
  tileH: 28.941176470588236,
};
const TILE_W = FIGMA_FIELD.tileW;
const TILE_H = FIGMA_FIELD.tileH;
const TILE = (29.5625 + 28.941176470588236) / 2;

const MAZE_ROWS = [
  "################",
  "#...#......#...#",
  "#####.####.#####",
  "##............##",
  "##.###.##.###.##",
  "##.#........#.##",
  "##.#.##.###.#.##",
  "##........#...##",
  "##.#.#.##.#.#.##",
  "##...#........##",
  "##.#.###.##.#.##",
  "##.#........#.##",
  "##.###.##.###.##",
  "##............##",
  "#####.####.#####",
  "#...#......#...#",
  "################",
];

const FIGMA_ENTITIES = {
  playerStart: { x: 3, y: 7, wx: 203.47, wy: 317.06 },
  ghostSpawns: [
    { id: "fomo", x: 5, y: 3, wx: 262.59, wy: 201.29 },
    { id: "inflation", x: 10, y: 3, wx: 410.41, wy: 201.29 },
    { id: "impulse", x: 4, y: 11, wx: 233.03, wy: 432.82 },
  ],
  portfolioTile: { x: 13, y: 10, wx: 499.09, wy: 403.88 },
};

/** Демо-монеты отключены — позиции только из сетки (cellWorld) */
const FIGMA_DEMO_PELLETS = [
  
];

const PELLET_WEIGHTS = { coin: 0.82, percent: 0.11, logo: 0.07 };

const SCORE_COIN = 10;
const SCORE_PERCENT = 25;
const SCORE_LOGO = 50;
const PORTFOLIO_DURATION_MS = 8000;

function cellWorld(gx, gy) {
  return {
    wx: FIGMA_FIELD.x + gx * TILE_W + TILE_W / 2,
    wy: FIGMA_FIELD.y + gy * TILE_H + TILE_H / 2,
  };
}

function floodReachable(rows, sx, sy) {
  const cols = rows[0].length;
  const seen = new Set();
  const key = (x, y) => `${x},${y}`;
  if (rows[sy][sx] === "#") return seen;
  const q = [[sx, sy]];
  seen.add(key(sx, sy));
  while (q.length) {
    const [x, y] = q.shift();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx;
      const ny = y + dy;
      const k = key(nx, ny);
      if (nx < 0 || ny < 0 || nx >= cols || ny >= rows.length) continue;
      if (rows[ny][nx] === "#" || seen.has(k)) continue;
      seen.add(k);
      q.push([nx, ny]);
    }
  }
  return seen;
}

const REACHABLE = floodReachable(MAZE_ROWS, FIGMA_ENTITIES.playerStart.x, FIGMA_ENTITIES.playerStart.y);

function worldToGrid(wx, wy) {
  return {
    x: Math.max(0, Math.min(MAZE_ROWS[0].length - 1, Math.round((wx - FIGMA_FIELD.x - TILE_W / 2) / TILE_W))),
    y: Math.max(0, Math.min(MAZE_ROWS.length - 1, Math.round((wy - FIGMA_FIELD.y - TILE_H / 2) / TILE_H))),
  };
}

function reservedCells() {
  const set = new Set();
  const mark = (x, y) => set.add(`${x},${y}`);
  mark(FIGMA_ENTITIES.playerStart.x, FIGMA_ENTITIES.playerStart.y);
  FIGMA_ENTITIES.ghostSpawns.forEach((g) => mark(g.x, g.y));
  if (FIGMA_ENTITIES.portfolioTile) mark(FIGMA_ENTITIES.portfolioTile.x, FIGMA_ENTITIES.portfolioTile.y);
  return set;
}

function pickPelletType() {
  const r = Math.random();
  if (r < PELLET_WEIGHTS.coin) return "coin";
  if (r < PELLET_WEIGHTS.coin + PELLET_WEIGHTS.percent) return "percent";
  return "logo";
}

function generateRandomPellets() {
  const reserved = reservedCells();
  const pellets = [];
  let n = 0;

  for (let y = 0; y < MAZE_ROWS.length; y++) {
    for (let x = 0; x < MAZE_ROWS[y].length; x++) {
      const k = `${x},${y}`;
      if (MAZE_ROWS[y][x] === "#") continue;
      if (!REACHABLE.has(k)) continue;
      if (reserved.has(k)) continue;

      const type = pickPelletType();
      const w = cellWorld(x, y);
      pellets.push({
        id: `r${n++}`,
        type,
        x,
        y,
        wx: w.wx,
        wy: w.wy,
        points: type === "percent" ? SCORE_PERCENT : type === "logo" ? SCORE_LOGO : SCORE_COIN,
      });
    }
  }
  return pellets;
}

function parseMaze() {
  const walls = [];
  for (let y = 0; y < MAZE_ROWS.length; y++) {
    for (let x = 0; x < MAZE_ROWS[y].length; x++) {
      const k = `${x},${y}`;
      if (MAZE_ROWS[y][x] === "#" || !REACHABLE.has(k)) walls.push({ x, y });
    }
  }

  return {
    cols: MAZE_ROWS[0].length,
    rows: MAZE_ROWS.length,
    walls,
    pellets: generateRandomPellets(),
    playerStart: { ...FIGMA_ENTITIES.playerStart },
    portfolioTile: { ...FIGMA_ENTITIES.portfolioTile },
    ghostSpawns: FIGMA_ENTITIES.ghostSpawns.map((g) => ({ ...g })),
  };
}

const MAZE = parseMaze();

window.KopilkaMaze = {
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
};
