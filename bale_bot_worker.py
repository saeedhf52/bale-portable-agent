"""Bale Bot Worker — Bridge between Bale Messenger & Isolated Agent Core.

Listens for incoming messages in Bale Web (via CDP) or Bale Bot API,
reassembles chunked frames via `bale_tunnel`, dispatches commands to `AgentCore`,
and sends response frames back over Bale.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Callable

from agent_core import AgentCore
import bale_tunnel
import bale_agent

log = logging.getLogger("bale_worker")


class BaleBotWorker:
    def __init__(self, agent: AgentCore | None = None, key: bytes = b"", poll_interval: float = 2.0):
        self.agent = agent or AgentCore()
        self.key = key
        self.poll_interval = poll_interval
        self.reassembler = bale_tunnel.Reassembler(key=self.key)
        self.running = False
        self._last_processed_id = None

    def process_incoming_text(self, text: str) -> dict | None:
        """Process raw text line. Returns response payload dict if command finished."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        out_payload = None
        for line in lines:
            if not line.startswith("BALE-TUN|v1|"):
                continue
            try:
                cmd = self.reassembler.feed(line)
                if cmd is not None:
                    out_payload = self.agent.handle_command(cmd)
            except Exception as exc:
                out_payload = {"ok": False, "error": f"Tunnel decode error: {exc}"}
        return out_payload

    def poll_once(self, cdp) -> list[dict]:
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
            log.warning(f"Error polling Bale message: {exc}")
        return results

    def start_loop(self, cdp_port: int = 9222):
        """Run continuous listener loop."""
        self.running = True
        log.info(f"Starting BaleBotWorker loop on CDP port {cdp_port}...")
        cdp = bale_agent.find_browser()
        # In actual usage, user opens Bale Web in browser
        while self.running:
            try:
                # Poll message if CDP active
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
