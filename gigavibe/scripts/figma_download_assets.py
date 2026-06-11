"""Download Figma localhost assets from ctx_*.txt into sprites/raw."""
from __future__ import annotations

import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CTX = ROOT / "web" / "assets" / "figma" / "_context"
OUT = ROOT / "web" / "assets" / "figma" / "sprites" / "raw"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for ctx_file in sorted(CTX.glob("ctx_*.txt")):
        text = ctx_file.read_text(encoding="utf-8")
        m = re.search(r'http://localhost:3845/assets/[a-f0-9]+\.png', text)
        if not m:
            print("skip", ctx_file.name)
            continue
        url = m.group(0)
        slug = ctx_file.stem.replace("ctx_", "")
        dest = OUT / f"{slug}.png"
        req = urllib.request.Request(url, headers={"User-Agent": "gigavibe-export/1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        dest.write_bytes(data)
        manifest.append({"slug": slug, "url": url, "bytes": len(data), "path": str(dest.relative_to(ROOT))})
        print(slug, len(data), "bytes")

    import json

    (OUT.parent / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
