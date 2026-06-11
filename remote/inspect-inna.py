#!/usr/bin/env python3
"""Проверка состояния VPS Inna."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
for cmd in [
    "hostname; curl -4 -s ifconfig.me; echo",
    "dig +short sberfest2026.ru A 2>/dev/null || getent hosts sberfest2026.ru",
    "ss -tlnp 2>/dev/null | head -20",
    "systemctl is-active photo-receiver 2>/dev/null || true",
    "systemctl is-active nginx 2>/dev/null || true",
]:
    run(c, cmd)
c.close()
