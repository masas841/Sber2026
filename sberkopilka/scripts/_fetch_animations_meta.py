#!/usr/bin/env python3
import json
import re
import urllib.request

url = "http://127.0.0.1:3845/mcp"
headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def parse_sse(text):
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


def mcp_session():
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fetch-anim", "version": "1"},
        },
    }
    req = urllib.request.Request(url, data=json.dumps(init).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        sid = r.headers.get("mcp-session-id")
        parse_sse(r.read().decode())
    h = dict(headers)
    h["mcp-session-id"] = sid
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    req = urllib.request.Request(url, data=json.dumps(notif).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    return h


def call_tool(h, name, args, req_id=2):
    body = {"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": name, "arguments": args}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = parse_sse(r.read().decode("utf-8", "replace"))
    if data.get("error"):
        raise RuntimeError(data["error"])
    return "".join(c.get("text", "") for c in data["result"]["content"] if c.get("type") == "text")


def main():
    h = mcp_session()

    # Current selection / page root
    for args in [
        {"clientLanguages": "javascript", "clientFrameworks": "react"},
        {"nodeId": "", "clientLanguages": "javascript", "clientFrameworks": "react"},
    ]:
        try:
            text = call_tool(h, "get_metadata", args, req_id=3)
            print("=== get_metadata no nodeId ===")
            print(text[:8000])
        except Exception as e:
            print("no nodeId failed:", e)

    # Scan known anchors and siblings
    candidates = list(range(1, 50)) + list(range(800, 900)) + list(range(1100, 1150)) + list(range(1300, 1350)) + list(range(2300, 2400)) + list(range(3500, 3600))
    hits = []
    for n in candidates:
        node = f"25:{n}"
        try:
            text = call_tool(h, "get_metadata", {"nodeId": node, "clientLanguages": "javascript", "clientFrameworks": "react"}, req_id=100 + n)
        except Exception:
            continue
        if "No node could be found" in text:
            continue
        names = re.findall(r'name="([^"]+)"', text)
        if not names:
            continue
        top = names[0]
        if re.search(r"(?i)анима|transition|prototype|flow|переход", top) or re.search(r"(?i)анима|transition|dissolve|шар|прокрут|ease|duration|move", text):
            hits.append((node, top, len(text)))
            print(f"HIT {node} name={top!r} len={len(text)}")
            for line in text.splitlines()[:40]:
                print(" ", line[:180])

    print("\nTotal hits:", len(hits))

    # Full design context for animation section if found
    for node, name, _ in hits[:3]:
        try:
            ctx = call_tool(h, "get_design_context", {"nodeId": node, "clientLanguages": "javascript", "clientFrameworks": "react"}, req_id=9000)
            out = f"i:\\Cursor\\Sber2026\\sberkopilka\\web\\assets\\figma\\_context\\_anim_{node.replace(':','_')}.txt"
            with open(out, "w", encoding="utf-8") as f:
                f.write(ctx)
            print("saved", out, "len", len(ctx))
        except Exception as e:
            print("context fail", node, e)


if __name__ == "__main__":
    main()
