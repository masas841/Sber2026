#!/usr/bin/env python3
"""Сохраняет JSX из Figma Desktop MCP в _context (запускать при обновлении макета)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "web" / "assets" / "figma" / "_context"

NODES = {
    "start": "25:1367",
    "onboarding_1": "25:868",
    "onboarding_2": "25:1125",
    "onboarding_3": "25:1323",
    "error": "25:1407",
    "result_score": "25:1632",
    "result_record": "25:1944",
    "leaderboard": "25:2181",
    "game": "25:6",
}


def extract_jsx(raw: str) -> str | None:
    if "export default" not in raw:
        return None
    # убрать хвост с SUPER CRITICAL
    idx = raw.find("SUPER CRITICAL")
    if idx > 0:
        raw = raw[:idx].rstrip()
    return raw.strip() + "\n"


def main() -> None:
    print("Сохраните JSX вручную через Cursor MCP get_design_context")
    print("или положите готовые файлы в", CTX)
    missing = [k for k in NODES if not (CTX / f"{k}.txt").exists()]
    ok = [k for k in NODES if (CTX / f"{k}.txt").exists() and "export default" in (CTX / f"{k}.txt").read_text(encoding="utf-8", errors="replace")]
    print(f"ready: {ok}")
    print(f"missing/incomplete: {missing}")


if __name__ == "__main__":
    main()
