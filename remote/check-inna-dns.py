#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inna_ssh import connect, run

c = connect()
run(c, "dig +short sberfest2026.ru @8.8.8.8")
run(c, "dig +short sberfest2026.ru @1.1.1.1")
run(c, "dig sberfest2026.ru NS +short")
run(c, "host sberfest2026.ru 8.8.8.8 || true")
run(c, "cat /etc/nginx/sites-enabled/photo-receiver")
run(c, "ss -tlnp")
run(c, "ufw status verbose 2>/dev/null || true")
run(c, "tail -30 /var/log/letsencrypt/letsencrypt.log")
run(c, "curl -sf http://45.67.59.125/api/health -H 'Host: sberfest2026.ru' || echo FAIL")
c.close()
