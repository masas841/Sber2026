#!/usr/bin/env python3
"""Деплой photo_receiver на VPS по паролю (один раз)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parent.parent
RECEIVER = ROOT / "photo_receiver"
REMOTE_DIR = "/opt/photo-receiver"


def ssh_connect(host: str, user: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)
    return client


def run(client: paramiko.SSHClient, cmd: str) -> None:
    print(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=600)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.rstrip())
    if err:
        print(err.rstrip(), file=sys.stderr)
    if code != 0:
        raise RuntimeError(f"exit {code}: {cmd}")


def upload_tree(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="45.67.59.125")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.environ.get("INNA_SSH_PASSWORD", ""))
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--public-url", default="https://sberfest2026.ru")
    args = parser.parse_args()
    if not args.password:
        print("Укажите --password или INNA_SSH_PASSWORD", file=sys.stderr)
        return 1

    client = ssh_connect(args.host, args.user, args.password)
    try:
        sftp = client.open_sftp()
        run(client, f"mkdir -p {REMOTE_DIR}")
        upload_tree(sftp, RECEIVER / "app", f"{REMOTE_DIR}/app")
        if (RECEIVER / "static").is_dir():
            upload_tree(sftp, RECEIVER / "static", f"{REMOTE_DIR}/static")
        sftp.put(str(RECEIVER / "requirements.txt"), f"{REMOTE_DIR}/requirements.txt")
        sftp.put(str(RECEIVER / ".env.example"), f"{REMOTE_DIR}/.env.example")
        sftp.put(str(RECEIVER / "install.sh"), f"{REMOTE_DIR}/install.sh")
        sftp.close()

        run(client, f"sed -i 's/\\r$//' {REMOTE_DIR}/install.sh")
        run(client, f"chmod +x {REMOTE_DIR}/install.sh")
        run(
            client,
            f"PUBLIC_URL={args.public_url} PORT={args.port} bash {REMOTE_DIR}/install.sh {REMOTE_DIR}",
        )
        run(client, f"curl -sf http://127.0.0.1:{args.port}/api/health")
        print("photo_receiver OK")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
