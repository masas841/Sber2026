#!/usr/bin/env python3
"""Парсит JSX из _context/*.txt → layouts/*.json (координаты 672×672)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "web" / "assets" / "figma" / "_context"
OUT = ROOT / "web" / "assets" / "figma" / "layouts"
BASE = "/static/assets/figma/shared"

SCREENS = [
    "start",
    "onboarding_1",
    "onboarding_2",
    "onboarding_3",
    "error",
    "result_score",
    "result_record",
    "leaderboard",
]

CONST_RE = re.compile(
    r'const\s+(\w+)\s*=\s*"http://localhost:3845/assets/([a-f0-9]+)\.(png|svg)"',
    re.I,
)
PX = re.compile(r"(-?[\d.]+)px")
CALC_LEFT = re.compile(r"left-\[calc\(50%([+-][\d.]+)px\)\]")
TEXT_COLOR = re.compile(r"text-\[(#[0-9a-fA-F]{3,8})\]")
TEXT_SIZE = re.compile(r"text-\[([\d.]+)px\]")


def parse_px(token: str, default: float | None = None) -> float | None:
    m = PX.search(token)
    return float(m.group(1)) if m else default


def parse_box(classes: str) -> dict | None:
    left = None
    top = None
    w = None
    h = None
    rot = 0.0
    ox = 0.0
    oy = 0.0

    for c in classes.split():
        if c.startswith("left-"):
            cm = CALC_LEFT.search(c)
            if cm:
                left = 336 + float(cm.group(1))
            else:
                left = parse_px(c)
        elif c.startswith("top-"):
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
            rot = parse_px(c, 0) or 0
        elif c == "-translate-x-1/2":
            ox = 0.5
        elif c == "-translate-y-1/2":
            oy = 0.5

    if left is None and top is None:
        return None
    if w is None and h is None and left is None:
        return None
    return {
        "x": left or 0,
        "y": top or 0,
        "w": w or 0,
        "h": h or 0,
        "rot": rot,
        "ox": ox,
        "oy": oy,
    }


def extract_layers_and_texts(content: str, consts: dict[str, str]) -> tuple[list, list]:
    layers: list[dict] = []
    texts: list[dict] = []

    # img blocks: div ... className="...absolute..." ... <img src={imgX}
    img_pat = re.compile(
        r'className="([^"]*absolute[^"]*)"[^>]*>[\s\S]*?<img[^>]+src=\{(\w+)\}',
        re.I,
    )
    for m in img_pat.finditer(content):
        box = parse_box(m.group(1))
        var = m.group(2)
        if not box or var not in consts:
            continue
        if box["w"] <= 0 and box["h"] <= 0:
            continue
        layers.append({**box, "file": consts[var]})

    # direct img with absolute parent one line
    simple_img = re.compile(
        r'<div className="([^"]*absolute[^"]*)"[^>]*>\s*<img[^>]+src=\{(\w+)\}',
        re.I,
    )
    for m in simple_img.finditer(content):
        box = parse_box(m.group(1))
        var = m.group(2)
        if not box or var not in consts:
            continue
        key = consts[var]
        if any(l.get("file") == key and abs(l["x"] - box["x"]) < 2 and abs(l["y"] - box["y"]) < 2 for l in layers):
            continue
        if box["w"] <= 0 and box["h"] <= 0:
            continue
        layers.append({**box, "file": key})

    # texts
    p_pat = re.compile(
        r'<p className="([^"]*)"[^>]*>([\s\S]*?)</p>',
        re.I,
    )
    for m in p_pat.finditer(content):
        cls, raw = m.group(1), m.group(2)
        if "{" in raw or "`" in raw:
            # template — take literal chunks
            parts = re.findall(r"['`]([^'`]+)['`]", raw)
            text = "".join(parts).replace("\\n", "\n").strip()
            if not text:
                br = "\n" if "<br" in raw else ""
                text = br.join(parts) if parts else ""
        else:
            text = raw.strip()
        if not text or text.startswith("{"):
            continue
        box = parse_box(cls)
        if not box:
            continue
        color_m = TEXT_COLOR.search(cls)
        size_m = TEXT_SIZE.search(cls)
        texts.append(
            {
                "x": box["x"],
                "y": box["y"],
                "ox": box["ox"] or 0.5,
                "text": text,
                "size": float(size_m.group(1)) if size_m else 16,
                "color": color_m.group(1) if color_m else "#122654",
                "bold": "Semibold" in cls or "font-['SB_Sans_Display" in cls,
            }
        )

    # dedupe layers by file+pos
    seen = set()
    uniq_layers = []
    for l in sorted(layers, key=lambda x: (x["y"], x["x"])):
        k = (l["file"], round(l["x"]), round(l["y"]), round(l["w"]), round(l["h"]))
        if k in seen:
            continue
        seen.add(k)
        uniq_layers.append(l)

    return uniq_layers, texts


def parse_screen(name: str) -> dict | None:
    path = CTX / f"{name}.txt"
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8", errors="replace")
    if "export default" not in content:
        return None
    consts = {m.group(1): f"{m.group(2)}.{m.group(3).lower()}" for m in CONST_RE.finditer(content)}
    layers, texts = extract_layers_and_texts(content, consts)

    bg = None
    bg_m = re.search(r'imgBgDecor\s*=\s*"[^"]+/([a-f0-9]+\.\w+)"', content)
    if bg_m:
        bg = bg_m.group(1)

    return {
        "id": name,
        "size": [672, 672],
        "bgDecor": bg,
        "layers": layers[:80],
        "texts": texts[:20],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_layouts = {}
    for name in SCREENS:
        layout = parse_screen(name)
        if not layout:
            print(f"skip {name}: no JSX")
            continue
        out = OUT / f"{name}.json"
        out.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
        all_layouts[name] = layout
        print(f"{name}: {len(layout['layers'])} layers, {len(layout['texts'])} texts")
    (OUT / "index.json").write_text(
        json.dumps(all_layouts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
