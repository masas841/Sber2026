"""Fetch Figma node metadata by id (Figma Desktop MCP)."""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

MCP_URL = "http://127.0.0.1:3845/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def read_sse(resp) -> dict | None:
    buf = resp.read().decode("utf-8", "replace")
    for line in buf.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


def main() -> int:
    node_id = sys.argv[1] if len(sys.argv) > 1 else "32:2"
    out = pathlib.Path(__file__).resolve().parents[1] / "web" / "assets" / "figma" / "_context" / f"node_{node_id.replace(':', '_')}.xml"

    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "g", "version": "1"}}}
    req = urllib.request.Request(MCP_URL, data=json.dumps(init).encode(), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        sid = r.headers.get("mcp-session-id")
        read_sse(r)
    h = dict(HEADERS)
    h["mcp-session-id"] = sid
    urllib.request.urlopen(urllib.request.Request(MCP_URL, data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}).encode(), headers=h, method="POST"), timeout=30).read()

    body = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_metadata", "arguments": {"nodeId": node_id, "clientLanguages": "html,css", "clientFrameworks": "vanilla"}}}
    with urllib.request.urlopen(urllib.request.Request(MCP_URL, data=json.dumps(body).encode(), headers=h, method="POST"), timeout=120) as r:
        data = read_sse(r)
    text = "".join(c.get("text", "") for c in data["result"]["content"] if c.get("type") == "text")
    out.write_text(text, encoding="utf-8")
    print("saved", out, "len", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
