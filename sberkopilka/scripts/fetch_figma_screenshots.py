#!/usr/bin/env python3
"""Сохраняет PNG-превью экранов через Figma Desktop MCP (127.0.0.1:3845)."""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "assets" / "figma" / "screens"
MCP = "http://127.0.0.1:3845/mcp"

SCREENS = {
    "start": "25:1367",
    "onboarding_1": "25:868",
    "onboarding_2": "25:1125",
    "onboarding_3": "25:1323",
    "error": "25:1407",
    "result_score": "25:1632",
    "result_record": "25:1944",
    "leaderboard": "25:2181",
}


def mcp_call(tool: str, arguments: dict) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    r = requests.post(MCP, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("result", data)


def extract_image_bytes(result) -> bytes | None:
    """Ищет base64 PNG/JPEG в ответе MCP."""
    text = json.dumps(result) if not isinstance(result, str) else result

    # data:image/png;base64,...
    m = re.search(r"data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)", text)
    if m:
        return base64.b64decode(m.group(1))

    # чистый base64 блок
    for blob in re.findall(r'"([A-Za-z0-9+/]{200,}={0,2})"', text):
        try:
            raw = base64.b64decode(blob)
            if raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:2] == b"\xff\xd8":
                return raw
        except Exception:
            continue
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, node_id in SCREENS.items():
        out = OUT / f"{name}.png"
        try:
            result = mcp_call("get_screenshot", {"nodeId": node_id})
            raw = extract_image_bytes(result)
            if not raw:
                print(f"skip {name}: no image in MCP response")
                continue
            out.write_bytes(raw)
            print(f"saved {out.name} ({len(raw)} bytes)")
            ok += 1
        except Exception as e:
            print(f"fail {name}: {e}")
    if ok == 0:
        print("No screenshots saved — is Figma Desktop MCP running?")
        sys.exit(1)


if __name__ == "__main__":
    main()
