#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
run(
    c,
    "certbot --nginx -d sberfest2026.ru --non-interactive --agree-tos "
    "-m admin@sberfest2026.ru --redirect",
    timeout=300,
)
run(c, "systemctl reload nginx")
run(c, "ss -tlnp | grep 443 || true")
run(c, "curl -sf http://127.0.0.1/api/health -H 'Host: sberfest2026.ru'")
run(c, "curl -sf https://sberfest2026.ru/api/health")
c.close()
