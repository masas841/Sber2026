#!/usr/bin/env python3
"""nginx + Let's Encrypt на Inna для sberfest2026.ru."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

ROOT = Path(__file__).resolve().parent.parent
REMOTE_DIR = "/opt/photo-receiver"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="sberfest2026.ru")
    parser.add_argument("--email", default="admin@sberfest2026.ru")
    args = parser.parse_args()

    client = connect()
    try:
        sftp = client.open_sftp()
        local = ROOT / "photo_receiver" / "setup-ssl.sh"
        sftp.put(str(local), f"{REMOTE_DIR}/setup-ssl.sh")
        sftp.close()

        run(client, f"sed -i 's/\\r$//' {REMOTE_DIR}/setup-ssl.sh")
        run(client, f"chmod +x {REMOTE_DIR}/setup-ssl.sh")
        run(
            client,
            f"DOMAIN={args.domain} EMAIL={args.email} bash {REMOTE_DIR}/setup-ssl.sh",
            timeout=900,
        )
        run(client, f"curl -sf https://{args.domain}/api/health")
        print(f"SSL OK: https://{args.domain}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
