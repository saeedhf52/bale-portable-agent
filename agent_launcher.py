"""Unified Master Launcher for Bale Portable AI Agent (OpenCode / Claude Code style).

Launches Web GUI Server, Bale Bot Worker, and Interactive Agent REPL in a single process.
"""
from __future__ import annotations

import argparse
import logging
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
from interactive_console import InteractiveConsole

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


def main():
    parser = argparse.ArgumentParser(description="Bale Portable AI Agent Master Launcher")
    parser.add_argument("--bot-token", help="Override Bale Bot API Token")
    parser.add_argument("--key", help="Override encryption key")
    parser.add_argument("--no-gui", action="store_true", help="Disable Web GUI")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode without REPL")
    args = parser.parse_args()

    db.init_db()

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
        console = InteractiveConsole()
        console.run()


if __name__ == "__main__":
    main()
