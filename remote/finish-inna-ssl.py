#!/usr/bin/env python3
"""Закрыть :8767 снаружи, проверить nginx, повторить certbot если DNS готов."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

DOMAIN = "sberfest2026.ru"
EMAIL = "admin@sberfest2026.ru"

c = connect()

run(c, "ufw delete allow 8767/tcp || true")
run(c, "ufw status numbered")

# убедиться что photo-receiver только localhost
run(c, "grep -E '^(HOST|PORT|PUBLIC_BASE_URL)=' /opt/photo-receiver/.env || true")
run(c, "systemctl is-active photo-receiver nginx")

ip = run(c, f"dig +short {DOMAIN} @8.8.8.8")[1].strip()
print(f"DNS A @8.8.8.8: {ip or 'NXDOMAIN'}")

if ip == "45.67.59.125":
    print("DNS OK — запуск certbot...")
    run(
        c,
        f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos "
        f"-m {EMAIL} --redirect",
        timeout=300,
    )
    run(c, "systemctl reload nginx")
    code, out, _ = run(c, f"curl -sf https://{DOMAIN}/api/health")
    if code == 0:
        print("HTTPS OK:", out.strip())
    else:
        print("HTTPS check failed")
else:
    print(
        f"DNS ещё не указывает на 45.67.59.125 - certbot пропущен.\n"
        f"Добавьте A-запись {DOMAIN} -> 45.67.59.125 в Beget, затем:\n"
        f"  python remote/run-certbot-inna.py"
    )
    run(c, f"curl -sf http://127.0.0.1/api/health -H 'Host: {DOMAIN}'")

c.close()
