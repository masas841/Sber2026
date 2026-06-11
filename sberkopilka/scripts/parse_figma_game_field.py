#!/usr/bin/env python3
"""Парсит game.txt → layouts/game-field.json (статические слои поля 672×672)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "assets" / "figma" / "_context" / "game.txt"
OUT = ROOT / "web" / "assets" / "figma" / "layouts" / "game-field.json"

CONST_RE = re.compile(
    r'const\s+(\w+)\s*=\s*"http://localhost:3845/assets/([a-f0-9]+)\.(png|svg)"',
    re.I,
)
WALL_VARS = {
    "img1020",
    "img5619343",
    "img793938",
    "img14189",
}
SKIP_NAMES = {"Герои", "Штуки на поле", "Портфель", "Счет", "Жизни"}
PX = re.compile(r"(-?[\d.]+)px")


def parse_px(token: str) -> float | None:
    m = PX.search(token)
    return float(m.group(1)) if m else None


def parse_classes(classes: str) -> dict:
    left = top = w = h = rot = None
    scale_y = 1
    for c in classes.split():
        if c.startswith("left-"):
            if "calc(50%" in c:
                m = re.search(r"calc\(50%([+-][\d.]+)px\)", c)
                left = 336 + float(m.group(1)) if m else 336
            else:
                left = parse_px(c)
        elif c.startswith("top-"):
            if "calc(50%" in c:
                m = re.search(r"calc\(50%([+-][\d.]+)px\)", c)
                top = 336 + float(m.group(1)) if m else 336
            else:
                top = parse_px(c)
        elif c.startswith("w-"):
            w = parse_px(c)
        elif c.startswith("h-"):
            h = parse_px(c)
        elif c.startswith("size-"):
            s = parse_px(c)
            if s:
                w = h = s
        elif c.startswith("rotate-"):
            rot = parse_px(c)
        elif c == "-scale-y-100":
            scale_y = -1
    return {"left": left, "top": top, "w": w, "h": h, "rot": rot or 0, "scaleY": scale_y}


def main() -> None:
    text = SRC.read_text(encoding="utf-8", errors="replace")
    const_map = {m.group(1): f"{m.group(2)}.{m.group(3).lower()}" for m in CONST_RE.finditer(text)}

    layers: list[dict] = []
    skip_depth = 0
    for line in text.splitlines():
        if 'data-name="' in line:
            m = re.search(r'data-name="([^"]+)"', line)
            if m and m.group(1) in SKIP_NAMES:
                skip_depth += 1
                continue
        if skip_depth > 0:
            if "<div" in line and "absolute" in line:
                pass
            if "</div>" in line:
                skip_depth = max(0, skip_depth - 1)
            continue

        if "src={" not in line:
            continue
        sm = re.search(r"src=\{(\w+)\}", line)
        if not sm or sm.group(1) not in WALL_VARS:
            continue

        # ищем ближайший absolute box выше (упрощённо — в той же зоне файла)
        layers.append({"var": sm.group(1), "file": const_map.get(sm.group(1), "")})

    # второй проход: div с wall var внутри
    blocks = re.findall(
        r'<div className="([^"]*)"[^>]*data-node-id="([^"]*)"[^>]*(?:data-name="([^"]*)")?[^>]*>'
        r"[\s\S]*?src=\{(\w+)\}",
        text,
    )
    seen = set()
    for classes, node_id, name, var in blocks:
        if var not in WALL_VARS:
            continue
        if name in SKIP_NAMES:
            continue
        box = parse_classes(classes)
        if box["left"] is None or box["top"] is None:
            continue
        if not box["w"] and not box["h"]:
            continue
        key = (node_id, var)
        if key in seen:
            continue
        seen.add(key)
        w = box["w"] or box["h"] or 40
        h = box["h"] or box["w"] or 40
        layers.append({
            "id": node_id,
            "name": name or "",
            "file": const_map.get(var, ""),
            "x": round(box["left"], 2),
            "y": round(box["top"], 2),
            "w": round(w, 2),
            "h": round(h, 2),
            "rot": box["rot"],
            "scaleY": box["scaleY"],
        })

    # дедуп по позиции
    uniq = []
    keys = set()
    for L in layers:
        if not L.get("file"):
            continue
        k = (L["file"], L.get("x"), L.get("y"), L.get("w"), L.get("h"))
        if k in keys:
            continue
        keys.add(k)
        uniq.append(L)

    chrome = {
        "bgDecor": "bd338f5b9b0f56d0bb2cc179fb704abde6cb4956.svg",
        "shadow1": "d0fdcdea6f470b21913662cbbe66c00de9890160.png",
        "shadow2": "7326c12827ced98e71e173542da09e8370c6df13.png",
        "fieldFrame": "3a438d68f2ba7c8c9e89444c4c2ab663223ad259.svg",
        "screenBorder": True,
    }

    out = {
        "size": [672, 672],
        "fieldOrigin": [107.52, 74.39],
        "tile": 24,
        "cols": 16,
        "rows": 17,
        "chrome": chrome,
        "walls": uniq,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(uniq)} wall layers")


if __name__ == "__main__":
    main()
