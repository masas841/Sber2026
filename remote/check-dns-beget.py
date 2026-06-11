#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
for cmd in [
    "host -t NS sberfest2026.ru ns1.beget.com",
    "host -t NS sberfest2026.ru ns2.beget.com",
    "dig sberfest2026.ru NS +short @ns1.beget.com",
    "dig sberfest2026.ru A +short @ns1.beget.com",
    "whois sberfest2026.ru 2>/dev/null | grep -iE 'nserver|state|status|paid' | head -15 || true",
]:
    run(c, cmd)
c.close()
