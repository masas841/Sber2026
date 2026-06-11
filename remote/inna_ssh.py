#!/usr/bin/env python3
"""SSH helper for Greathearted Inna (photo_receiver)."""

from __future__ import annotations

import os
import sys

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise SystemExit(1)


def connect(host: str = "45.67.59.125", user: str = "root", password: str | None = None) -> paramiko.SSHClient:
    password = password or os.environ.get("INNA_SSH_PASSWORD", "")
    if not password:
        raise RuntimeError("INNA_SSH_PASSWORD not set")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 600, quiet: bool = False) -> tuple[int, str, str]:
    if not quiet:
        print(f"$ {cmd}", flush=True)
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out and not quiet:
        try:
            print(out.rstrip(), flush=True)
        except UnicodeEncodeError:
            print(out.rstrip().encode("ascii", errors="replace").decode("ascii"), flush=True)
    if err and not quiet:
        print(err.rstrip(), file=sys.stderr, flush=True)
    return code, out, err
