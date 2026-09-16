"""Agent Core — orchestrator glueing skills, automation engine, RAG, and tunnel.

Single entry point:

    agent = AgentCore()
    agent.run_skill("smart_login", {"url": "...", "username": "..."})
    agent.handle_command({"cmd": "run", "skill": "..."})

Isolated from web UI; usable from CLI, Bale bot, or MCP server.
"""
from __future__ import annotations

import json
import logging
import time
import traceback
from typing import Any

import automation_engine
import automation_db
import skill_manager

log = logging.getLogger("agent_core")


class AgentCore:
    def __init__(self, port: int = 9222):
        self.port = port
        self.context: dict[str, Any] = {}
        automation_db.init_db()

    # ---------- Skills ----------

    def list_skills(self) -> list[dict]:
        return skill_manager.list_skills()

    def run_skill(self, name: str, args: dict | None = None) -> dict:
        skill = skill_manager.get_skill(name)
        args = args or {}
        started = time.time()
        try:
            if skill["kind"] == "recipe":
                steps = skill["steps"]
                # inject args as variables
                merged_steps = [{"action": "set_variable", "key": k, "value": v} for k, v in args.items()] + steps
                results = automation_engine.run_automation_steps(merged_steps, port=self.port)
                out = {"ok": True, "kind": "recipe", "results": results}
            else:  # python
                fn = skill_manager.load_python_skill(skill["path"])
                res = fn(self.context, args)
                out = {"ok": True, "kind": "python", "result": res}
        except Exception as exc:
            out = {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-2000:]}
        out["duration_ms"] = int((time.time() - started) * 1000)
        automation_db.add_log(None, "ok" if out["ok"] else "error",
                              f"skill:{name}", {"args": args, "result": out})
        return out

    def install_skill(self, name: str, kind: str, content: str) -> dict:
        path = skill_manager.install_skill(name, kind, content)
        return {"ok": True, "path": path}

    # ---------- Command dispatch (bot/tunnel entry point) ----------

    COMMANDS = {"run", "install", "list", "status", "ask"}

    def handle_command(self, cmd: dict) -> dict:
        op = cmd.get("cmd")
        if op not in self.COMMANDS:
            return {"ok": False, "error": f"unknown command: {op}"}
        try:
            if op == "run":
                return self.run_skill(cmd["skill"], cmd.get("args", {}))
            if op == "install":
                return self.install_skill(cmd["name"], cmd["kind"], cmd["content"])
            if op == "list":
                return {"ok": True, "skills": self.list_skills()}
            if op == "status":
                return {"ok": True, "port": self.port, "context_keys": list(self.context)}
            if op == "ask":
                # Pending question → pass through to gateway via tunnel; handled elsewhere.
                return {"ok": True, "queued": True, "question": cmd.get("prompt", "")}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-2000:]}
        return {"ok": False, "error": "unreachable"}


# ---- self-check ----
if __name__ == "__main__":
    a = AgentCore()
    r = a.handle_command({"cmd": "list"})
    assert r["ok"]
    r = a.handle_command({"cmd": "status"})
    assert r["ok"] and r["port"] == 9222
    r = a.handle_command({"cmd": "bogus"})
    assert not r["ok"]
    print("agent_core self-check OK")
