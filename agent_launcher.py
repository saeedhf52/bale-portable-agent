"""Unified Master Launcher for Bale Portable AI Agent (OpenCode / Claude Code style).

Launches Web GUI Server, Bale Bot Worker, and Interactive Agent REPL in a single process.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import automation_db as db
from agent_core import AgentCore
from bale_bot_worker import BaleBotWorker
from web_gui import AgentRequestHandler, HTTPServer, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("agent_launcher")


def start_web_gui_thread():
    server = HTTPServer(("127.0.0.1", PORT), AgentRequestHandler)
    log.info(f"🌐 Web GUI listening on http://127.0.0.1:{PORT}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def start_bot_worker_thread(bot_token: str, tunnel_key: bytes = b""):
    if not bot_token:
        log.info("ℹ️ Bale Bot Token not configured. Worker bot disabled (configure in Web GUI or CLI).")
        return None
    worker = BaleBotWorker(bot_token=bot_token, key=tunnel_key)
    thread = threading.Thread(target=worker.start_loop, kwargs={"mode": "bot_api"}, daemon=True)
    thread.start()
    log.info("🤖 Bale Bot Worker started in HTTP long-poll mode.")
    return worker


def run_repl(agent: AgentCore):
    print("\n" + "=" * 60)
    print(" 🤖 Bale Portable AI Agent — Interactive Shell (type 'help' or 'exit')")
    print("=" * 60)
    while True:
        try:
            line = input("\nagent> ").strip()
            if not line:
                continue
            if line in {"exit", "quit"}:
                print("👋 Bye!")
                break
            if line == "help":
                print("Commands:\n  list              List all installed skills")
                print("  run <skill> [args] Execute a skill")
                print("  ask <prompt>       Query RAG knowledge memory")
                print("  set-bot <token>   Set Bale Bot API token")
                print("  status            Show system status")
                continue

            parts = line.split(maxsplit=1)
            cmd = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

            if cmd == "list":
                skills = agent.list_skills()
                print(json.dumps(skills, ensure_ascii=False, indent=2))

            elif cmd == "run":
                sp = rest.split(maxsplit=1)
                sname = sp[0] if sp else ""
                sargs = json.loads(sp[1]) if len(sp) > 1 else {}
                res = agent.run_skill(sname, sargs)
                print(json.dumps(res, ensure_ascii=False, indent=2))

            elif cmd == "ask":
                res = db.search_knowledge(rest)
                print(json.dumps(res, ensure_ascii=False, indent=2))

            elif cmd == "set-bot":
                db.set_setting("bot_token", rest)
                print(f"✅ Bale Bot Token saved: {rest[:8]}...")

            elif cmd == "status":
                from bale_agent import probe_endpoint
                active = probe_endpoint(9222)
                token = db.get_setting("bot_token")
                print(f"  Browser CDP (9222): {'✅ Active' if active else '❌ Inactive'}")
                print(f"  Web GUI (8080):    ✅ Active")
                print(f"  Bale Bot API:      {'✅ Configured' if token else '⚠️ Token not set'}")

            else:
                # Handle arbitrary JSON command payload
                if line.startswith("{"):
                    obj = json.loads(line)
                    res = agent.handle_command(obj)
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for instructions.")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as exc:
            print(f"❌ Error: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Bale Portable AI Agent Master Launcher")
    parser.add_argument("--bot-token", help="Override Bale Bot API Token")
    parser.add_argument("--key", help="Override encryption key")
    parser.add_argument("--no-gui", action="store_true", help="Disable Web GUI")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode without REPL")
    args = parser.parse_args()

    db.init_db()
    agent = AgentCore()

    if args.bot_token:
        db.set_setting("bot_token", args.bot_token)
    if args.key:
        db.set_setting("tunnel_key", args.key)

    bot_token = db.get_setting("bot_token")
    tunnel_key = db.get_setting("tunnel_key").encode() if db.get_setting("tunnel_key") else b""

    if not args.no_gui:
        start_web_gui_thread()

    if bot_token:
        start_bot_worker_thread(bot_token, tunnel_key)

    if args.daemon:
        log.info("Agent running in daemon mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("Daemon stopped.")
    else:
        run_repl(agent)


if __name__ == "__main__":
    main()
