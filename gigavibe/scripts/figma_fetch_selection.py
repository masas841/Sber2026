"""Fetch current Figma Desktop selection via local MCP (127.0.0.1:3845)."""
from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

MCP_URL = "http://127.0.0.1:3845/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
OUT = pathlib.Path(__file__).resolve().parents[1] / "web" / "assets" / "figma" / "_context"


def read_sse(resp) -> dict | None:
    buf = ""
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        buf += chunk.decode("utf-8", "replace")
    event_lines: list[str] = []
    for line in buf.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith("data: "):
            event_lines.append(line[6:])
        elif line == "" and event_lines:
            payload = "\n".join(event_lines).replace("\u2028", "\\n").replace("\u2029", "\\n")
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                OUT.mkdir(parents=True, exist_ok=True)
                (OUT / "selection_mcp_raw.sse").write_text(buf, encoding="utf-8")
                (OUT / "selection_mcp_payload.txt").write_text(payload, encoding="utf-8")
                raise
    if event_lines:
        payload = "\n".join(event_lines).replace("\u2028", "\\n").replace("\u2029", "\\n")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "selection_mcp_raw.sse").write_text(buf, encoding="utf-8")
            (OUT / "selection_mcp_payload.txt").write_text(payload, encoding="utf-8")
            raise
    return None


def mcp_session():
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "gigavibe-export", "version": "1"},
        },
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(init).encode(), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        sid = r.headers.get("mcp-session-id")
        read_sse(r)
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    h = dict(HEADERS)
    h["mcp-session-id"] = sid
    req = urllib.request.Request(MCP_URL, data=json.dumps(notif).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        read_sse(r)
    return sid, h


def call_tool(sid, h, name: str, args: dict, req_id: int) -> dict:
    body = {"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": name, "arguments": args}}
    req = urllib.request.Request(MCP_URL, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        data = read_sse(r)
    if not data:
        raise RuntimeError(f"{name}: empty MCP response")
    if data.get("error"):
        raise RuntimeError(f"{name}: {data['error']}")
    return data


def text_from_result(data: dict) -> str:
    return "".join(c.get("text", "") for c in data["result"].get("content", []) if c.get("type") == "text")


def parse_nodes(xml: str) -> list[dict]:
    pat = re.compile(
        r'<(?P<type>frame|group|component|instance|rounded-rectangle|ellipse|vector|boolean-operation|text)'
        r' id="(?P<id>[^"]+)" name="(?P<name>[^"]*)"'
        r'(?: x="(?P<x>[^"]*)")?(?: y="(?P<y>[^"]*)")?'
        r'(?: width="(?P<w>[^"]*)")?(?: height="(?P<h>[^"]*)")?'
    )
    return [m.groupdict() for m in pat.finditer(xml)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sid, h = mcp_session()

    meta = call_tool(
        sid,
        h,
        "get_metadata",
        {"clientLanguages": "html,css,javascript", "clientFrameworks": "vanilla"},
        2,
    )
    xml = text_from_result(meta)
    (OUT / "selection_metadata.xml").write_text(xml, encoding="utf-8")

    nodes = parse_nodes(xml)
    summary = {
        "node_count": len(nodes),
        "nodes": nodes,
    }
    (OUT / "selection_nodes.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {len(nodes)} nodes to selection_nodes.json")
    for n in nodes[:50]:
        print(
            f"  {n['id']:12} {n['type']:22} {n['name'][:48]:48} "
            f"{n.get('w') or '?'}x{n.get('h') or '?'}"
        )
    if len(nodes) > 50:
        print(f"  ... and {len(nodes) - 50} more")

    # design context may include asset URLs
    try:
        ctx = call_tool(
            sid,
            h,
            "get_design_context",
            {"clientLanguages": "html,css,javascript", "clientFrameworks": "vanilla"},
            3,
        )
        ctx_text = text_from_result(ctx)
        (OUT / "selection_design_context.txt").write_text(ctx_text, encoding="utf-8")
        print(f"design_context: {len(ctx_text)} chars")
        # extract http asset urls
        urls = re.findall(r"https://[^\s\"')]+", ctx_text)
        if urls:
            (OUT / "selection_asset_urls.json").write_text(
                json.dumps(sorted(set(urls)), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"asset URLs: {len(set(urls))}")
    except Exception as e:
        print(f"design_context skipped: {e}", file=sys.stderr)

    for node_id, label in [
        ("14:12", "reference_giga0"),
        ("14:37", "logo"),
        ("14:41", "logo_backplate"),
        ("14:47", "tagline_pill"),
        ("14:49", "front_flower_left"),
        ("14:50", "front_flower_right"),
    ]:
        try:
            ctx = call_tool(
                sid,
                h,
                "get_design_context",
                {
                    "nodeId": node_id,
                    "clientLanguages": "html,css,javascript",
                    "clientFrameworks": "vanilla",
                },
                100 + len(label),
            )
            ctx_text = text_from_result(ctx)
            (OUT / f"selection_{label}_design_context.txt").write_text(ctx_text, encoding="utf-8")
            print(f"{label}: {len(ctx_text)} chars")
        except Exception as e:
            print(f"{label} skipped: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
