"""Bale Bot Worker — Bridge between Bale Messenger & Isolated Agent Core.

Listens for incoming messages via Bale Bot API (long-polling) or Bale Web (via CDP),
reassembles chunked frames via `bale_tunnel`, OR converts natural language requests into
automations using AI Gateway, dispatches commands to `AgentCore`, and sends responses back.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.parse
from typing import Callable

from agent_core import AgentCore
import bale_tunnel
import bale_agent
from gateway import ai_gateway

log = logging.getLogger("bale_worker")
BALE_API_BASE = "https://tapi.bale.ai/bot"


class BaleBotWorker:
    def __init__(self, agent: AgentCore | None = None, bot_token: str = "", key: bytes = b"", poll_interval: float = 2.0):
        self.agent = agent or AgentCore()
        self.bot_token = bot_token
        self.key = key
        self.poll_interval = poll_interval
        self.reassembler = bale_tunnel.Reassembler(key=self.key)
        self.running = False
        self._last_processed_id = None
        self._last_update_id = 0

    def process_incoming_text(self, text: str) -> dict | None:
        """Process raw text line (tunnel frame OR natural language AI command)."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        out_payload = None

        for line in lines:
            # 1. Tunnel frame processing
            if line.startswith("BALE-TUN|v1|"):
                try:
                    cmd = self.reassembler.feed(line)
                    if cmd is not None:
                        out_payload = self.agent.handle_command(cmd)
                except Exception as exc:
                    out_payload = {"ok": False, "error": f"Tunnel decode error: {exc}"}
                continue

            # 2. Plain text / Natural language AI command
            log.info(f"🤖 Bale Bot received natural language prompt: '{line}'")
            try:
                # Use AI Gateway to synthesize recipe from prompt
                synth = ai_gateway.synthesize(line)
                steps = synth.get("steps", [])
                if not steps:
                    out_payload = {"ok": False, "error": "AI could not generate steps for this prompt."}
                    continue

                cmd_payload = {"cmd": "run", "steps": steps}
                out_payload = self.agent.handle_command(cmd_payload)
                out_payload["ai_synthesized"] = True
                out_payload["steps_count"] = len(steps)
            except Exception as exc:
                log.error(f"AI synthesis error in bot worker: {exc}")
                out_payload = {"ok": False, "error": f"AI Processing Error: {exc}"}

        return out_payload

    # ── Bale Bot API (HTTP Long Polling) ──
    def send_bot_message(self, chat_id: int | str, text: str) -> bool:
        """Send a message using official Bale Bot API."""
        if not self.bot_token:
            log.warning("bot_token not set, skipping API send")
            return False
        url = f"{BALE_API_BASE}{self.bot_token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("ok", False)
        except Exception as exc:
            log.error(f"Failed to send Bale message: {exc}")
            return False

    def poll_bot_api(self) -> list[tuple[int | str, dict]]:
        """Long poll updates from Bale Bot API."""
        if not self.bot_token:
            return []
        url = f"{BALE_API_BASE}{self.bot_token}/getUpdates?offset={self._last_update_id + 1}&timeout=10"
        req = urllib.request.Request(url)
        results = []
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data.get("ok"):
                    return []
                updates = data.get("result", [])
                for u in updates:
                    self._last_update_id = max(self._last_update_id, u.get("update_id", 0))
                    msg = u.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    if text and chat_id:
                        res = self.process_incoming_text(text)
                        if res:
                            results.append((chat_id, res))
        except Exception as exc:
            log.warning(f"Error polling Bale Bot API: {exc}")
        return results

    # ── CDP Polling (Bale Web fallback) ──
    def poll_once_cdp(self, cdp) -> list[dict]:
        """Poll latest unread message from open Bale chat via CDP adapter."""
        results = []
        try:
            msg_state = bale_agent.adapter_call(cdp, "message")
            msg = msg_state.get("message")
            if msg and msg.get("direction") == "incoming":
                mid = msg.get("id") or msg.get("epoch_ms")
                if mid != self._last_processed_id:
                    self._last_processed_id = mid
                    text = msg.get("text", "")
                    res = self.process_incoming_text(text)
                    if res:
                        results.append(res)
        except Exception as exc:
            log.warning(f"Error polling Bale message via CDP: {exc}")
        return results

    def start_loop(self, mode: str = "bot_api"):
        """Run continuous listener loop ('bot_api' or 'cdp')."""
        self.running = True
        log.info(f"Starting BaleBotWorker in {mode} mode...")

        if mode == "bot_api" and not self.bot_token:
            raise ValueError("bot_token is required for bot_api mode")

        cdp = bale_agent.find_browser() if mode == "cdp" else None

        while self.running:
            try:
                if mode == "bot_api":
                    for chat_id, res in self.poll_bot_api():
                        # If simple text response for natural language bot chat
                        if res.get("ai_synthesized"):
                            reply_text = f"🤖 اتوماسیون با موفقیت اجرا شد:\n" + json.dumps(res.get("results", []), ensure_ascii=False, indent=2)[:3500]
                            self.send_bot_message(chat_id, reply_text)
                        else:
                            # Frame tunnel response
                            frames = bale_tunnel.encode(res, key=self.key)
                            for frame in frames:
                                self.send_bot_message(chat_id, frame)
                elif mode == "cdp" and cdp:
                    self.poll_once_cdp(cdp)
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                break
        self.running = False


# ---- self-check ----
if __name__ == "__main__":
    worker = BaleBotWorker(key=b"secret")
    payload = {"cmd": "list"}
    frames = bale_tunnel.encode(payload, key=b"secret")
    res = None
    for f in frames:
        res = worker.process_incoming_text(f)
    assert res is not None and res.get("ok"), "Worker command handling failed"
    print("bale_bot_worker self-check OK")
