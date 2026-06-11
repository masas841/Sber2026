#!/usr/bin/env python3
"""Записывает полный JSX из Figma MCP в _context/*.txt (обновлять при смене макета)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "assets" / "figma" / "_context"

# Вставьте сюда полный ответ get_design_context (до SUPER CRITICAL)
FILES: dict[str, str] = {}


def strip_footer(text: str) -> str:
    i = text.find("SUPER CRITICAL")
    return (text[:i] if i > 0 else text).strip() + "\n"


def main() -> None:
    if not FILES:
        print("FILES пуст — добавьте JSX из Figma MCP get_design_context")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in FILES.items():
        path = OUT / f"{name}.txt"
        path.write_text(strip_footer(body), encoding="utf-8")
        print("wrote", path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
