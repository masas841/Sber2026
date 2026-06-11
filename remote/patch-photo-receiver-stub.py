#!/usr/bin/env python3
"""Быстрый деплой app/ + static/ на Inna."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

ROOT = Path(__file__).resolve().parent.parent
RECEIVER = ROOT / "photo_receiver"
REMOTE = "/opt/photo-receiver"


def upload_tree(sftp, local: Path, remote: str) -> None:
    if local.is_file():
        sftp.put(str(local), remote)
        return
    try:
        sftp.mkdir(remote)
    except OSError:
        pass
    for item in local.iterdir():
        if item.name in {".venv", "data", "__pycache__", ".env"}:
            continue
        rpath = f"{remote}/{item.name}"
        if item.is_dir():
            upload_tree(sftp, item, rpath)
        else:
            sftp.put(str(item), rpath)


def main() -> int:
    c = connect()
    sftp = c.open_sftp()
    upload_tree(sftp, RECEIVER / "app", f"{REMOTE}/app")
    upload_tree(sftp, RECEIVER / "static", f"{REMOTE}/static")
    sftp.close()
    run(c, "systemctl restart photo-receiver")
    run(c, "sleep 2 && curl -sf http://127.0.0.1:8767/api/health")
    run(c, "curl -sf https://sberfest2026.ru/ | head -8")
    c.close()
    print("stub deployed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
