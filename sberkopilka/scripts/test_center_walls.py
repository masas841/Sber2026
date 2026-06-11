#!/usr/bin/env python3
import build_maze_from_figma as bf
from collections import deque

walls = bf.parse_walls(bf.SRC.read_text(encoding="utf-8"))
OX, OY, TILE = bf.OX, bf.OY, bf.TILE
COLS, ROWS = bf.COLS, bf.ROWS

def center(gx, gy):
    return OX + gx * TILE + TILE / 2, OY + gy * TILE + TILE / 2

def is_wall_center(gx, gy):
    cx, cy = center(gx, gy)
    for l, t, w, h in walls:
        if l <= cx <= l + w and t <= cy <= t + h:
            return True
    return False

def flood(grid, sx, sy):
    seen={(sx,sy)}; q=deque([(sx,sy)])
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<COLS and 0<=ny<ROWS and grid[ny][nx]!='#' and (nx,ny) not in seen:
                seen.add((nx,ny)); q.append((nx,ny))
    return seen

player = next(e for e in bf.FIGMA_ENTITIES if e["role"]=="player")
pgx = int((player["cx"]-OX-TILE/2)/TILE)
pgy = int((player["cy"]-OY-TILE/2)/TILE)

grid = [['#' if is_wall_center(gx,gy) else '.' for gx in range(COLS)] for gy in range(ROWS)]
for x in range(COLS):
    grid[0][x]=grid[ROWS-1][x]='#'
for y in range(ROWS):
    grid[y][0]=grid[y][COLS-1]='#'

reach = flood(grid, pgx, pgy)
print('reachable', len(reach), 'walkable', sum(r.count('.') for r in [''.join(r) for r in grid]))
for row in [''.join(r) for r in grid]:
    print(row)

# markers
for e in bf.FIGMA_ENTITIES + [{"cx":p["cx"],"cy":p["cy"]} for p in bf.FIGMA_PELLETS]:
    gx = round((e["cx"]-OX-TILE/2)/TILE)
    gy = round((e["cy"]-OY-TILE/2)/TILE)
    ok = (gx,gy) in reach
    print(f"  ({gx},{gy}) walk={grid[gy][gx]=='.'} reach={ok}  {e.get('role',e.get('type','pellet'))}")
