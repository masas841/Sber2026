#!/usr/bin/env python3
"""Скриншот figma-screens/*.html → web/assets/figma/screens/*.png (672×672)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "web" / "figma-screens"
OUT = ROOT / "web" / "assets" / "figma" / "screens"
BASE_URL = "http://127.0.0.1:8766/static/figma-screens"
SIZE = 672

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


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE})
        for name in SCREENS:
            html = PAGES / f"{name}.html"
            if not html.exists():
                print(f"skip {name}: no html")
                continue
            url = f"{BASE_URL}/{name}.html"
            try:
                page.on("console", lambda msg: print(f"  [{name}] {msg.type}: {msg.text}"))
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_selector("#root img, #root [class*='gradient']", timeout=30000)
                page.wait_for_timeout(800)
                target = page.locator("#capture")
                out = OUT / f"{name}.png"
                target.screenshot(path=str(out), type="png")
                size = out.stat().st_size
                print(f"saved {out.name} ({size} bytes)")
                if size < 8000:
                    print(f"  warn: {name} preview looks empty (<8KB)")
                ok += 1
            except Exception as e:
                print(f"fail {name}: {e}")
        browser.close()

    if ok == 0:
        print("No previews captured — start server: python -m app.main")
        sys.exit(1)


if __name__ == "__main__":
    main()
