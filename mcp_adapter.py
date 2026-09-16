"""Minimal Model Context Protocol (MCP) adapter — stdio JSON-RPC 2.0.

Exposes the agent's skills as MCP tools to any MCP-compatible client (Claude
Desktop, Cursor, etc.). Runs as a subprocess reading requests from stdin and
writing responses to stdout. Line-delimited JSON, per MCP spec 2024-11-05.

Not a full MCP implementation — only `initialize`, `tools/list`, `tools/call`
and `ping`. Enough to expose the agent to a host without pulling a heavy SDK.
"""
from __future__ import annotations

import json
import sys
import traceback

from agent_core import AgentCore


class MCPServer:
    PROTOCOL = "2024-11-05"

    def __init__(self, agent: AgentCore | None = None):
        self.agent = agent or AgentCore()

    def _tools(self) -> list[dict]:
        tools = []
        for s in self.agent.list_skills():
            tools.append({
                "name": s["name"],
                "description": s.get("description") or f"{s['kind']} skill",
                "inputSchema": {"type": "object", "additionalProperties": True},
            })
        return tools

    def handle(self, req: dict) -> dict | None:
        rpc_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        try:
            if method == "initialize":
                result = {"protocolVersion": self.PROTOCOL,
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "bale-portable-agent", "version": "0.1.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._tools()}
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("arguments", {}) or {}
                out = self.agent.run_skill(name, args)
                text = json.dumps(out, ensure_ascii=False)
                result = {"content": [{"type": "text", "text": text}],
                          "isError": not out.get("ok", False)}
            elif method and method.startswith("notifications/"):
                return None  # notifications get no reply
            else:
                return {"jsonrpc": "2.0", "id": rpc_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}}
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": rpc_id,
                    "error": {"code": -32603, "message": str(exc), "data": traceback.format_exc()[-500:]}}

    def serve(self, stdin=sys.stdin, stdout=sys.stdout):
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = self.handle(req)
            if resp is not None:
                stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                stdout.flush()


# ---- self-check ----
if __name__ == "__main__":
    import io
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        MCPServer().serve()
    else:
        srv = MCPServer()
        r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert r["result"]["protocolVersion"] == MCPServer.PROTOCOL
        r = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert "tools" in r["result"]
        r = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "unknown"})
        assert r["error"]["code"] == -32601
        print("mcp_adapter self-check OK")
