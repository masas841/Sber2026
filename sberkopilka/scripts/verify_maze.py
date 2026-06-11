#!/usr/bin/env python3
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from maze_constants import COLS, ROWS

text = Path(__file__).resolve().parents[1] / "web" / "js" / "maze.js"
body = text.read_text(encoding="utf-8")
rows = re.findall(r'"([^"]+)"', body.split("const MAZE_ROWS = [")[1].split("];")[0])
ents = {"player": (13, 12), "g1": (6, 5), "g2": (12, 5), "g3": (5, 13), "P": (4, 12)}
assert len(rows) == ROWS, (len(rows), ROWS)
for i, r in enumerate(rows):
    assert len(r) == COLS, (i, len(r), r)
    print(f"{i:2} {r}")
print("--- entities ---")
for name, (x, y) in ents.items():
    ch = rows[y][x]
    print(name, x, y, ch, "OK" if ch != "#" else "WALL!")
