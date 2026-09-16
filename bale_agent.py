"""Local Bale Web exporter. No AI service, browser driver, or runtime pip needed."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
for wheel in sorted((ROOT / "vendor").glob("*.whl")):
    sys.path.insert(0, str(wheel))

TEHRAN = dt.timezone(dt.timedelta(hours=3, minutes=30), "Tehran")
BALE_HOST = "web.bale.ai"
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class AgentError(Exception):
    pass


def log(message):
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or "utf-8"
            print(str(message).encode(encoding, errors="replace").decode(encoding, errors="replace"), flush=True)
        except Exception:
            pass


def local_url(url, schemes):
    """Never allow a discovered CDP endpoint to redirect us off the machine."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in schemes or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise AgentError("CDP endpoint must be on localhost.")
    if parsed.username or parsed.password:
        raise AgentError("Credentials in a CDP URL are not supported.")
    return parsed


def endpoint_targets(port):
    url = f"http://127.0.0.1:{port}/json/list"
    with LOCAL_HTTP.open(url, timeout=2) as response:
        local_url(response.url, {"http"})
        return json.load(response)


def select_target(targets, target_id=None):
    candidates = []
    for target in targets:
        parsed = urllib.parse.urlsplit(target.get("url", ""))
        if (target.get("type") == "page" and parsed.scheme == "https"
                and parsed.hostname == BALE_HOST and target.get("webSocketDebuggerUrl")):
            candidates.append(target)
    if target_id:
        candidates = [t for t in candidates if t.get("id") == target_id]
    if candidates:
        if len(candidates) > 1:
            ids = ", ".join(t["id"] for t in candidates)
            log(f"⚠️ چند تب بله پیدا شد. از اولین تب استفاده می‌شود: {ids}")
        return candidates[0]

    # No open Bale tab — find any page target and automatically navigate to Bale Web
    page_targets = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not page_targets:
        raise AgentError("هیچ زبانه مرورگری یافت نشد.")

    target = page_targets[0]
    log("🌐 زبانه بله در مرورگر یافت نشد. هدایت خودکار به https://web.bale.ai/chat ...")
    try:
        cdp = CDP(target["webSocketDebuggerUrl"], timeout=15)
        cdp.call("Page.navigate", {"url": "https://web.bale.ai/chat"})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            url = cdp.evaluate("window.location.href")
            if BALE_HOST in str(url):
                break
            time.sleep(1)
        cdp.close()
        time.sleep(2)
    except Exception as exc:
        log(f"⚠️ خطا در هدایت خودکار مرورگر: {exc}")

    return target


class CDP:
    """One synchronous, localhost-only DevTools connection."""
    def __init__(self, url, timeout=20):
        local_url(url, {"ws"})
        try:
            import websocket
        except ImportError as exc:
            raise AgentError("Missing vendor dependency. Use the complete portable ZIP.") from exc
        self.timeout = timeout
        self.serial = 0
        self.ws = websocket.create_connection(
            url, timeout=timeout, suppress_origin=True,
            http_no_proxy=["localhost", "127.0.0.1", "::1"],
        )

    def close(self):
        self.ws.close()

    def call(self, method, params=None):
        self.serial += 1
        request_id = self.serial
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            raw = self.ws.recv()
            if not raw:
                raise AgentError("WebSocket connection lost.")
            msg = json.loads(raw)
            if msg.get("id") == request_id:
                if "error" in msg:
                    raise AgentError(f"CDP {method} failed: {msg['error'].get('message')}")
                return msg.get("result", {})
        raise AgentError(f"Timed out waiting for CDP response ({method}).")

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
            "awaitPromise": True, "userGesture": True,
        })
        exception_details = result.get("exceptionDetails")
        if exception_details:
            text = exception_details.get("text", "JS exception")
            value = exception_details.get("exception", {}).get("description") or text
            raise AgentError(f"JavaScript evaluation failed: {value}")
        return result.get("result", {}).get("value")
