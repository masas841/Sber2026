#!/usr/bin/env python3
import build_maze_from_figma as bf
from collections import deque

walls = bf.parse_walls(bf.SRC.read_text(encoding="utf-8"))
COLS, ROWS = bf.COLS, bf.ROWS

def flood(grid, sx, sy):
    if grid[sy][sx] == '#': return set()
    seen={(sx,sy)}; q=deque([(sx,sy)])
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<COLS and 0<=ny<ROWS and grid[ny][nx]!='#' and (nx,ny) not in seen:
                seen.add((nx,ny)); q.append((nx,ny))
    return seen

for th in [0.50,0.52,0.54,0.56,0.58,0.60,0.62]:
    grid=[['.' for _ in range(COLS)] for _ in range(ROWS)]
    for gy in range(ROWS):
        for gx in range(COLS):
            if max(bf.overlap_ratio(l,t,w,h,gx,gy) for l,t,w,h in walls) >= th:
                grid[gy][gx]='#'
    for x in range(COLS):
        grid[0][x]=grid[ROWS-1][x]='#'
    for y in range(ROWS):
        grid[y][0]=grid[y][COLS-1]='#'
    reach=flood(grid,13,12)
    cells=[(6,5),(12,5),(5,13),(2,12)]
    flags=''.join('.' if c in reach else '#' for c in cells)
    print(f'{th:.2f} reach={len(reach):2d} ghosts[{flags}] row5={grid[5]}')
