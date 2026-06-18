from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_EXCLUDE_DIRS = {
    ".cursor",
    ".git",
    ".idea",
    ".venv",
    ".venv-liveportrait",
    ".aigo123",
    "backups",
    "certs",
    "dist",
    "runtime",
    "tools",
    "__pycache__",
}
DEFAULT_EXCLUDE_PARTS = {
    ("data",),
    ("install", "redist"),
    ("install", "wheels"),
}
DEFAULT_EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".whl",
}
DEFAULT_EXCLUDE_NAMES = {
    ".env",
    "update-manifest.json",
    "update-manifest.local.json",
}
TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".css",
    ".example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".svg",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}
TEXT_NAMES = {
    ".env.example",
    ".gitignore",
}


def parse_exclude_parts(values: list[str]) -> set[tuple[str, ...]]:
    parts: set[tuple[str, ...]] = set()
    for value in values:
        normalized = value.strip().replace("\\", "/").strip("/")
        if normalized:
            parts.add(tuple(normalized.split("/")))
    return parts


def should_skip(
    path: Path,
    root: Path,
    exclude_dirs: set[str],
    exclude_parts: set[tuple[str, ...]],
    exclude_suffixes: set[str],
    exclude_names: set[str],
) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) == 1 and path.name.startswith(".") and path.name != ".env.example":
        return True
    if any(part in exclude_dirs for part in parts):
        return True
    if any(parts[: len(excluded)] == excluded for excluded in exclude_parts):
        return True
    if path.name in exclude_names:
        return True
    if path.suffix.lower() in exclude_suffixes:
        return True
    return False


def manifest_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build kiosk update manifest")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--name", required=True, help="Manifest root name (repo subdir)")
    parser.add_argument(
        "--exclude-part",
        action="append",
        default=[],
        help="Relative path prefix to exclude, e.g. web/assets/figma/_context",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude anywhere in tree",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = root / "install" / "update-manifest.json"
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)
    exclude_parts = DEFAULT_EXCLUDE_PARTS | parse_exclude_parts(args.exclude_part)

    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(
            path,
            root,
            exclude_dirs,
            exclude_parts,
            DEFAULT_EXCLUDE_SUFFIXES,
            DEFAULT_EXCLUDE_NAMES,
        ):
            continue
        rel = path.relative_to(root).as_posix()
        data = manifest_bytes(path)
        files.append(
            {
                "path": rel,
                "sha256": sha256(data),
                "size": len(data),
            }
        )

    payload = {
        "version": 1,
        "root": args.name,
        "files": files,
    }
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"update manifest: {out} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
