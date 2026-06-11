#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
for cmd in [
    "whois sberfest2026.ru 2>/dev/null | grep -i state",
    "dig sberfest2026.ru NS +short @a.dns.ripn.net",
    "dig sberfest2026.ru A +short @a.dns.ripn.net",
    "dig sberfest2026.ru NS +short @8.8.8.8",
    "dig sberfest2026.ru A +short @8.8.8.8",
]:
    run(c, cmd)
c.close()
