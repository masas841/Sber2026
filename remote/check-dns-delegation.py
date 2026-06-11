#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
for cmd in [
    "dig sberfest2026.ru NS +short @8.8.8.8",
    "dig sberfest2026.ru A +short @8.8.8.8",
    "dig sberfest2026.ru A +short @1.1.1.1",
    "dig sberfest2026.ru SOA +noall +answer @8.8.8.8",
    "dig sberfest2026.ru NS +trace | tail -20",
    "host -t NS sberfest2026.ru 8.8.8.8 || true",
    "host sberfest2026.ru ns1.beget.com 2>/dev/null || host sberfest2026.ru ns1.beget.pro 2>/dev/null || true",
]:
    run(c, cmd)
c.close()
