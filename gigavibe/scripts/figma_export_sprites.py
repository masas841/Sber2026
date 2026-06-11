"""Export selected Figma overlay sprites as PNG (per node)."""
from __future__ import annotations

import json
import pathlib
import re
import urllib.request

MCP_URL = "http://127.0.0.1:3845/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "assets" / "figma" / "sprites"
CTX = ROOT / "web" / "assets" / "figma" / "_context"

NODES = [
    {"id": "11:378", "slug": "sheet_2090010258"},
    {"id": "64:242", "slug": "composite_3_4"},
    {"id": "64:244", "slug": "composite_1_10"},
    {"id": "64:245", "slug": "composite_2_3"},
    {"id": "9:212", "slug": "image_2090010223"},
    {"id": "9:206", "slug": "image_2090010221"},
    {"id": "7:150", "slug": "image_2090010215"},
    {"id": "9:215", "slug": "image_2090010224"},
    {"id": "9:209", "slug": "image_2090010222"},
    {"id": "9:203", "slug": "image_2090010220"},
]


def read_sse(resp) -> dict | None:
    buf = ""
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        buf += chunk.decode("utf-8", "replace")
    for line in buf.splitlines():
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
    if not data or data.get("error"):
        raise RuntimeError(f"{name} {args}: {data}")
    return data


def text_from(data: dict) -> str:
    return "".join(c.get("text", "") for c in data["result"].get("content", []) if c.get("type") == "text")


def extract_urls(text: str) -> list[str]:
    return sorted(set(re.findall(r"https://[^\s\"')\\]+", text)))


def download(url: str, dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "gigavibe-export/1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sid, h = mcp_session()
    manifest: list[dict] = []
    req_id = 10

    for node in NODES:
        nid = node["id"]
        slug = node["slug"]
        entry = {"id": nid, "slug": slug, "files": [], "urls": [], "notes": []}

        # structure / asset refs
        try:
            ctx = call_tool(
                sid,
                h,
                "get_design_context",
                {
                    "nodeId": nid,
                    "clientLanguages": "html,css,javascript",
                    "clientFrameworks": "vanilla",
                },
                req_id,
            )
            req_id += 1
            ctx_text = text_from(ctx)
            (CTX / f"ctx_{slug}.txt").write_text(ctx_text, encoding="utf-8")
            urls = extract_urls(ctx_text)
            entry["urls"] = urls
            for i, url in enumerate(urls):
                ext = ".png" if ".png" in url.lower() else ".bin"
                dest = OUT / "raw" / f"{slug}_asset{i}{ext}"
                try:
                    download(url, dest)
                    entry["files"].append(str(dest.relative_to(ROOT)))
                except Exception as e:
                    entry["notes"].append(f"asset download failed: {e}")
        except Exception as e:
            entry["notes"].append(f"design_context: {e}")

        # rendered PNG from Figma (isolated node)
        for contents_only in (True, False):
            try:
                shot = call_tool(
                    sid,
                    h,
                    "get_screenshot",
                    {
                        "nodeId": nid,
                        "contentsOnly": contents_only,
                        "maxDimension": 2048,
                    },
                    req_id,
                )
                req_id += 1
                shot_text = text_from(shot)
                (CTX / f"shot_{slug}_{'iso' if contents_only else 'full'}.txt").write_text(
                    shot_text, encoding="utf-8"
                )
                urls = extract_urls(shot_text)
                if urls:
                    suffix = "iso" if contents_only else "full"
                    dest = OUT / f"{slug}_{suffix}.png"
                    download(urls[0], dest)
                    entry["files"].append(str(dest.relative_to(ROOT)))
                    break
            except Exception as e:
                entry["notes"].append(f"screenshot({contents_only}): {e}")

        manifest.append(entry)
        print(slug, "->", len(entry["files"]), "files", entry["notes"] or "ok")

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
