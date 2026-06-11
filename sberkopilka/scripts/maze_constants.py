"""Размеры игрового поля (сетка лабиринта)."""

COLS = 16

ROWS = 17

FIELD_W = 473

FIELD_H = 492

OX, OY = 107.52, 74.39

TILE_W = FIELD_W / COLS

TILE_H = FIELD_H / ROWS

TILE = (TILE_W + TILE_H) / 2  # средний шаг — скорость, радиусы


