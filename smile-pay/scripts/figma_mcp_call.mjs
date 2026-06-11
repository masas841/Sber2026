// CLI wrapper around local Figma Desktop MCP server.
// Usage:
//   node scripts/figma_mcp_call.mjs metadata 128:109 > out.txt
//   node scripts/figma_mcp_call.mjs context 127:513 > out.txt
//   node scripts/figma_mcp_call.mjs tools
//
// Output is written to stdout AND to scripts/figma_out/<name>.txt

import { writeFileSync, mkdirSync } from "node:fs";
import { Buffer } from "node:buffer";

const BASE = "http://127.0.0.1:3845/mcp";
const OUT_DIR = "scripts/figma_out";

function parseBody(text, contentType) {
  if (contentType && contentType.includes("text/event-stream")) {
    const chunks = [];
    for (const line of text.split(/\r?\n/)) {
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        if (payload && payload !== "[DONE]") {
          try { chunks.push(JSON.parse(payload)); } catch { /* skip */ }
        }
      }
    }
    return chunks;
  }
  try { return [JSON.parse(text)]; } catch { return [{ raw: text }]; }
}

async function rpc(method, params, sessionId) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (sessionId) headers["Mcp-Session-Id"] = sessionId;
  const res = await fetch(BASE, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params }),
  });
  const text = await res.text();
  const ct = res.headers.get("content-type") || "";
  return {
    status: res.status,
    session: res.headers.get("mcp-session-id"),
    messages: parseBody(text, ct),
  };
}

async function init() {
  const r = await rpc("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "figma-cli", version: "1.0" },
  });
  const session = r.session;
  if (session) {
    await fetch(BASE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
        "Mcp-Session-Id": session,
      },
      body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }),
    }).catch(() => {});
  }
  return session;
}

function extractText(messages) {
  // MCP tools return result.content = [{type:'text', text:'...'}]
  const out = [];
  for (const m of messages) {
    const content = m?.result?.content;
    if (Array.isArray(content)) {
      for (const c of content) {
        if (c.type === "text" && typeof c.text === "string") out.push(c.text);
        else out.push(JSON.stringify(c));
      }
    } else {
      out.push(JSON.stringify(m, null, 2));
    }
  }
  return out.join("\n");
}

function extractImages(messages) {
  // MCP image content: { type:'image', data:'<base64>', mimeType:'image/png' }
  const images = [];
  for (const m of messages) {
    const content = m?.result?.content;
    if (Array.isArray(content)) {
      for (const c of content) {
        if (c.type === "image" && typeof c.data === "string") {
          images.push({ data: c.data, mime: c.mimeType || "image/png" });
        }
      }
    }
  }
  return images;
}

(async () => {
  const [cmd, nodeId] = process.argv.slice(2);
  mkdirSync(OUT_DIR, { recursive: true });
  const session = await init();

  let result;
  let label;
  if (cmd === "tools") {
    result = await rpc("tools/list", {}, session);
    label = "tools";
    const body = JSON.stringify(result.messages, null, 2);
    writeFileSync(`${OUT_DIR}/${label}.json`, body);
    console.log(body);
    return;
  }

  const toolName = cmd === "metadata" ? "get_metadata"
    : cmd === "context" ? "get_design_context"
    : cmd === "shot" ? "get_screenshot"
    : null;
  if (!toolName || !nodeId) {
    console.error("Usage: node figma_mcp_call.mjs <metadata|context|shot|tools> [nodeId]");
    process.exit(1);
  }

  const args = { nodeId, clientLanguages: "javascript,html,css", clientFrameworks: "vanilla" };
  if (cmd === "shot" && process.argv[4] === "isolated") args.contentsOnly = true;
  result = await rpc("tools/call", { name: toolName, arguments: args }, session);
  label = `${cmd}_${nodeId.replace(/[:]/g, "-")}`;

  if (cmd === "shot") {
    const images = extractImages(result.messages);
    if (images.length === 0) {
      const text = extractText(result.messages);
      writeFileSync(`${OUT_DIR}/${label}.txt`, text);
      console.log(`[no image] status ${result.status}; saved raw to ${OUT_DIR}/${label}.txt`);
      return;
    }
    images.forEach((img, i) => {
      const ext = img.mime.includes("jpeg") ? "jpg" : "png";
      const file = `${OUT_DIR}/${label}${images.length > 1 ? `_${i}` : ""}.${ext}`;
      writeFileSync(file, Buffer.from(img.data, "base64"));
      console.log(`[saved] ${file}  (${Math.round(img.data.length * 0.75 / 1024)} KB)`);
    });
    return;
  }

  const text = extractText(result.messages);
  writeFileSync(`${OUT_DIR}/${label}.txt`, text);
  console.log(`[saved] ${OUT_DIR}/${label}.txt  (status ${result.status}, ${text.length} chars)`);
})();
