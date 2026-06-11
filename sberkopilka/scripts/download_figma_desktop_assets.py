#!/usr/bin/env python3
"""Скачивает ассеты из ответов Figma Desktop MCP (localhost:3845)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGMA = ROOT / "web" / "assets" / "figma"
CONTEXT_DIR = FIGMA / "_context"
BASE = "http://127.0.0.1:3845/assets"

SCREENS = {
    "start": {"nodeId": "25:1367", "name": "Start"},
    "onboarding_1": {"nodeId": "25:868", "name": "Onboarding_1"},
    "onboarding_2": {"nodeId": "25:1125", "name": "Onboarding_2"},
    "onboarding_3": {"nodeId": "25:1323", "name": "Onboarding_3"},
    "game": {"nodeId": "25:6", "name": "Game"},
    "error": {"nodeId": "25:1407", "name": "Error"},
    "result_score": {"nodeId": "25:1632", "name": "ResultScore"},
    "result_record": {"nodeId": "25:1944", "name": "ResultRecord"},
    "leaderboard": {"nodeId": "25:2181", "name": "Leaderboard"},
}

URL_RE = re.compile(
    r'http://localhost:3845/assets/([a-f0-9]+)\.(png|svg|jpg|jpeg|webp)',
    re.I,
)


def extract_urls(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for m in URL_RE.finditer(text):
        h, ext = m.group(1), m.group(2).lower()
        found[h] = ext
    return found


def download(hash_id: str, ext: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{hash_id}.{ext}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"  FAIL {dest.name}: {e}")
        return False


def process_screen(key: str, meta: dict) -> dict:
    ctx_file = CONTEXT_DIR / f"{key}.txt"
    if not ctx_file.exists():
        print(f"skip {key}: no context file")
        return {"nodeId": meta["nodeId"], "name": meta["name"], "assets": 0}

    text = ctx_file.read_text(encoding="utf-8", errors="replace")
    urls = extract_urls(text)
    screen_dir = FIGMA / key
    screen_dir.mkdir(parents=True, exist_ok=True)
    shared_dir = FIGMA / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, str] = {}
    downloaded = 0
    for h, ext in sorted(urls.items()):
        fname = f"{h}.{ext}"
        mapping[h] = fname
        if download(h, ext, shared_dir / fname):
            downloaded += 1
        # symlink-like copy: hardlink if possible else skip (shared pool)
        link = screen_dir / fname
        src = shared_dir / fname
        if src.exists() and not link.exists():
            try:
                link.hardlink_to(src)
            except OSError:
                link.write_bytes(src.read_bytes())

    manifest = {
        "nodeId": meta["nodeId"],
        "name": meta["name"],
        "size": {"width": 672, "height": 672},
        "assetCount": len(urls),
        "assets": mapping,
    }
    (screen_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{key}: {len(urls)} assets, {downloaded} new downloads")
    return manifest


def main() -> None:
    index = {"screens": {}, "shared": str(FIGMA / "shared")}
    for key, meta in SCREENS.items():
        index["screens"][key] = process_screen(key, meta)
    (FIGMA / "manifest.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"done -> {FIGMA / 'manifest.json'}")


if __name__ == "__main__":
    main()
