import json
import urllib.request
import pathlib

url = "http://127.0.0.1:3845/mcp"
headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
BASE = pathlib.Path(r"i:\Cursor\Sber2026\sberkopilka\web\assets\figma\_context")

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
            "clientInfo": {"name": "subagent", "version": "1"},
        },
    }
    req = urllib.request.Request(url, data=json.dumps(init).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        sid = r.headers.get("mcp-session-id")
        parse_sse(r.read().decode())
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    h = dict(headers)
    h["mcp-session-id"] = sid
    req = urllib.request.Request(url, data=json.dumps(notif).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    return sid

def call_tool(sid, name, args, req_id=2):
    body = {"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": name, "arguments": args}}
    h = dict(headers)
    h["mcp-session-id"] = sid
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return parse_sse(r.read().decode("utf-8", "replace"))

sid = mcp_session()
nodes = ["25:1632", "25:1944", "25:2181"]
for i, node in enumerate(nodes, start=10):
    data = call_tool(
        sid,
        "get_design_context",
        {"nodeId": node, "clientLanguages": "javascript", "clientFrameworks": "react"},
        req_id=i,
    )
    if data.get("error"):
        print(node, "ERROR", data["error"])
        continue
    content = data["result"]["content"]
    text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
    safe = node.replace(":", "_")
    out = BASE / f"_tmp_fetch_{safe}.raw"
    out.write_text(text, encoding="utf-8")
    print(node, "len", len(text), "export", "export default" in text)
