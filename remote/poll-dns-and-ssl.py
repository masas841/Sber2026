#!/usr/bin/env python3
"""Опрос публичного DNS; при готовности — certbot + проверка HTTPS."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

DOMAIN = "sberfest2026.ru"
EXPECTED_IP = "45.67.59.125"
EMAIL = "admin@sberfest2026.ru"
INTERVAL_SEC = 60
MAX_ATTEMPTS = 90  # ~90 min


def dns_ready(client) -> bool:
    _, out, _ = run(client, f"dig +short {DOMAIN} A @8.8.8.8", quiet=True)
    ip = out.strip().split("\n")[0].strip() if out.strip() else ""
    return ip == EXPECTED_IP


def whois_state(client) -> str:
    _, out, _ = run(client, f"whois {DOMAIN} 2>/dev/null | grep -i '^state:'", quiet=True)
    return out.strip()


def issue_ssl(client) -> bool:
    code, _, _ = run(
        client,
        f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos "
        f"-m {EMAIL} --redirect",
        timeout=300,
    )
    if code != 0:
        return False
    run(client, "systemctl reload nginx")
    time.sleep(2)
    code, out, _ = run(client, f"curl -sf https://{DOMAIN}/api/health")
    if code == 0:
        print(f"HTTPS OK: {out.strip()}")
        return True
    print("certbot finished but HTTPS health check failed")
    return False


def main() -> int:
    print(f"Polling {DOMAIN} -> {EXPECTED_IP} every {INTERVAL_SEC}s (max {MAX_ATTEMPTS} tries)")
    client = connect()
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            state = whois_state(client)
            _, dig_out, _ = run(client, f"dig +short {DOMAIN} A @8.8.8.8", quiet=True)
            ip = dig_out.strip().split("\n")[0].strip() if dig_out.strip() else "NXDOMAIN"
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] attempt {attempt}/{MAX_ATTEMPTS} WHOIS={state} A@8.8.8.8={ip}", flush=True)

            if dns_ready(client):
                print("DNS ready — issuing SSL...")
                if issue_ssl(client):
                    run(client, "ss -tlnp | grep -E ':443|:80' || true")
                    print(f"DONE: https://{DOMAIN}")
                    return 0
                return 1

            if attempt < MAX_ATTEMPTS:
                time.sleep(INTERVAL_SEC)
    finally:
        client.close()

    print("Timeout: DNS still not propagated")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
