from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "install" / "update-manifest.json"

EXCLUDE_DIRS = {
    ".cursor",
    ".git",
    ".idea",
    ".venv",
    ".venv-liveportrait",
    ".aigo123",
    "backups",
    "certs",
    "dist",
    "gfpgan",
    "models",
    "runtime",
    "tools",
    "vendor",
    "__pycache__",
}
EXCLUDE_PARTS = {
    ("assets", "driving"),
    ("assets", "video"),
    ("data", "jobs"),
    ("data", "outputs"),
    ("data", "uploads"),
    ("install", "redist"),
    ("install", "wheels"),
}
EXCLUDE_SUFFIXES = {
    ".onnx",
    ".pth",
    ".pyc",
    ".pyo",
    ".safetensors",
    ".whl",
}
EXCLUDE_NAMES = {
    ".env",
    "site-packages.zip",
    "update-manifest.json",
    "update-manifest.local.json",
}


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if len(parts) == 1 and path.name.startswith(".") and path.name != ".env.example":
        return True
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if any(parts[: len(excluded)] == excluded for excluded in EXCLUDE_PARTS):
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if path.suffix.lower() in {".mp4", ".mov", ".avi", ".webm"}:
        return rel.as_posix() != "assets/fon.mp4"
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        files.append(
            {
                "path": rel,
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )

    payload = {
        "version": 1,
        "root": "gigavibe",
        "files": files,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"update manifest: {OUT} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
