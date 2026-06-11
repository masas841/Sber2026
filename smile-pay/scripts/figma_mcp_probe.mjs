// Probe local Figma Desktop MCP server (http://127.0.0.1:3845/mcp).
// Performs initialize handshake + tools/list. Parses SSE or JSON responses.

const BASE = "http://127.0.0.1:3845/mcp";

function parseBody(text, contentType) {
  // SSE: lines like "data: {...}"
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

(async () => {
  try {
    const init = await rpc("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "figma-probe", version: "1.0" },
    });
    console.log("INIT status:", init.status, "session:", init.session);
    console.log("INIT body:", JSON.stringify(init.messages, null, 2));

    const session = init.session;
    if (session) {
      // notifications/initialized (no response expected)
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

    const tools = await rpc("tools/list", {}, session);
    console.log("TOOLS status:", tools.status);
    console.log("TOOLS body:", JSON.stringify(tools.messages, null, 2));
  } catch (err) {
    console.error("PROBE ERROR:", err.message);
  }
})();
