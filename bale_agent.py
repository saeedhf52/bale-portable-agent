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
    print(message, flush=True)


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
    if not candidates:
        raise AgentError("Open https://web.bale.ai/chat in the agent browser first.")
    if len(candidates) > 1:
        ids = ", ".join(t["id"] for t in candidates)
        raise AgentError(f"Several Bale tabs found. Close duplicates or use --target-id. IDs: {ids}")
    return candidates[0]


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
            self.ws.settimeout(max(.1, deadline - time.monotonic()))
            raw = self.ws.recv()
            if not raw:
                raise AgentError("Browser connection closed.")
            response = json.loads(raw)
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise AgentError(f"Browser error: {response['error'].get('message', 'unknown')}")
            return response.get("result", {})
        raise AgentError(f"Timeout during {method}.")

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
            "awaitPromise": True, "timeout": int(self.timeout * 1000),
        })
        if result.get("exceptionDetails"):
            detail = result["exceptionDetails"]
            raise AgentError(detail.get("exception", {}).get("description", detail.get("text", "Page error")))
        return result.get("result", {}).get("value")


def adapter_call(cdp, operation, argument=None):
    # No private API, app state, cookies, session stores, or network interception.
    source = (ROOT / "page_adapter.js").read_text(encoding="utf-8")
    return cdp.evaluate(f"({source})({json.dumps(operation)},{json.dumps(argument, ensure_ascii=False)})")


def wait_until(fn, predicate, timeout, description, interval=.15):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = fn()
        if predicate(last):
            return last
        time.sleep(interval)
    raise AgentError(f"Timed out: {description}.")


def find_browser(explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not path.is_file():
            raise AgentError(f"Browser executable not found: {path}")
        return path
    for env, suffix in [
        ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
        ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
        ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
        ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
    ]:
        base = os.environ.get(env)
        if base and (Path(base) / suffix).is_file():
            return Path(base) / suffix
    raise AgentError("Chrome/Edge not found. Supply --browser with its executable path.")


def launch_browser(args):
    try:
        targets = endpoint_targets(args.port)
    except (OSError, ValueError):
        targets = None
    if targets is not None:
        log(f"A debugging browser is already listening on port {args.port}.")
        return
    if args.port < 1024 or args.port > 65535:
        raise AgentError("Use a port between 1024 and 65535.")
    # Browser credentials belong to this Windows user and machine; do not bundle them.
    profile = Path(args.profile).resolve() if args.profile else Path(
        os.environ.get("LOCALAPPDATA", str(Path.home()))
    ) / "BalePortableAgent" / "BrowserProfile"
    default_suffixes = ("google/chrome/user data", "microsoft/edge/user data")
    if str(profile).replace("\\", "/").lower().endswith(default_suffixes):
        raise AgentError("Use a separate browser profile, not the normal Chrome/Edge profile.")
    browser = find_browser(args.browser)
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        str(browser), f"--remote-debugging-port={args.port}",
        "--remote-debugging-address=127.0.0.1", f"--user-data-dir={profile}",
        "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
        "--disable-component-update", "--disable-sync", "--new-window",
        "https://web.bale.ai/chat",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_until(lambda: probe_endpoint(args.port), bool, 20, "browser startup")
    log(f"Browser ready. Sign in to Bale manually. Profile: {profile}")
    log("Then run export-10.cmd. Login is needed once per destination machine.")


def probe_endpoint(port):
    try:
        endpoint_targets(port)
        return True
    except (OSError, ValueError):
        return False


def kill_browser_processes():
    """Kill any Chrome/Edge processes started with our debug profile."""
    import signal
    try:
        # taskkill by window title or profile path marker
        subprocess.run(
            ["taskkill", "/F", "/FI", "WINDOWTITLE eq *BalePortableAgent*"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
    except Exception:
        pass
    # Also try killing by port binding
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "chrome.exe", "/FI", "STATUS eq RUNNING"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
    except Exception:
        pass


def ensure_browser_ready(port=9222, browser_path=None, start_url=None, timeout=25):
    """Check browser connectivity. If dead/stuck, restart it. Returns True when ready."""
    # 1. Quick probe
    if probe_endpoint(port):
        # Verify WebSocket actually works
        try:
            targets = endpoint_targets(port)
            pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            if pages:
                cdp = CDP(pages[0]["webSocketDebuggerUrl"], timeout=5)
                cdp.evaluate("1+1")  # heartbeat
                cdp.close()
                log("✅ مرورگر فعال و آماده است.")
                return True
        except Exception as exc:
            log(f"⚠️ مرورگر پاسخ‌گو نیست: {exc}")

    # 2. Browser not responding — try to kill stale processes
    log("🔄 تلاش برای راه‌اندازی مجدد مرورگر...")
    kill_browser_processes()
    time.sleep(2)

    # 3. Launch fresh browser
    browser = find_browser(browser_path)
    profile = Path(
        os.environ.get("LOCALAPPDATA", str(Path.home()))
    ) / "BalePortableAgent" / "BrowserProfile"
    profile.mkdir(parents=True, exist_ok=True)

    url = start_url or "about:blank"
    subprocess.Popen([
        str(browser), f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1", f"--user-data-dir={profile}",
        "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
        "--disable-component-update", "--disable-sync", "--new-window", url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4. Wait for it
    try:
        wait_until(lambda: probe_endpoint(port), bool, timeout, "browser startup")
        log("✅ مرورگر با موفقیت راه‌اندازی شد.")
        return True
    except AgentError:
        log("❌ مرورگر راه‌اندازی نشد.")
        return False


def jalali_date(date):
    """Gregorian -> Solar Hijri arithmetic conversion, for modern calendar dates."""
    gy, gm, gd = date.year, date.month, date.day
    offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + offsets[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm, jd = (1 + days // 31, 1 + days % 31) if days < 186 else (7 + (days - 186) // 30, 1 + (days - 186) % 30)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def finalize_record(row, message):
    record = {"contact": row["name"], "row_index": row["index"], **message}
    stamp = float(record["epoch_ms"])
    when = dt.datetime.fromtimestamp(stamp / 1000, TEHRAN)
    record.update(timestamp=when.isoformat(), jalali_date=jalali_date(when), time=when.strftime("%H:%M"))
    return record


def render_text(report):
    fa = {"incoming": "مخاطب (دریافتی)", "outgoing": "شما (ارسالی)", "unknown": "نامشخص"}
    lines = [
        "آخرین پیام گفت‌وگوهای شخصی اخیر بله", f"زمان استخراج: {report['collected_at']}",
        f"وضعیت: {'کامل' if report['complete'] else 'ناقص — خطاها را بررسی کنید'}",
        f"تعداد ثبت‌شده: {len(report['messages'])} از {report['requested_count']}",
        "مبنا: آخرین پیام هر گفت‌وگو، اعم از ارسالی یا دریافتی؛ جدیدترین پیام در ابتدای فایل.",
        "فضای شخصی و اعلان صرف پیوستن به بله کنار گذاشته می‌شوند.",
        "برای رسانه، متن همراه و مشخصات قابل مشاهده ثبت می‌شود؛ تصویر یا صدا پیاده‌سازی نمی‌شود.",
        "زمان‌ها به وقت تهران است. پیام‌ها در زمان مشاهده هر گفت‌وگو ثبت شده‌اند.", "",
    ]
    for index, record in enumerate(report["messages"], 1):
        lines.extend([
            "─" * 60, f"{index}. مخاطب: {record['contact']}",
            f"تاریخ: {record['jalali_date']}", f"ساعت: {record['time']}",
            f"فرستنده: {fa.get(record['direction'], 'نامشخص')}", f"نوع: {record['kind']}",
        ])
        if record.get("forwarded_from"):
            lines.append(f"بازارسال‌شده از: {record['forwarded_from']}")
        if record.get("reply_to"):
            lines.append(f"پاسخ به: {record['reply_to']}")
        lines.extend(["متن / مشخصات پیام:", record.get("text") or "[بدون متن همراه]"])
        if record.get("media_details"):
            lines.append(record["media_details"])
        lines.append("")
    if report["errors"]:
        lines.append("موارد ناموفق:")
        lines.extend(f"- {e}" for e in report["errors"])
    return "\n".join(lines) + "\n"


def save_report(report, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    suffix = dt.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    base = output / ("bale_recent_" + suffix)
    text_path, json_path = base.with_suffix(".txt"), base.with_suffix(".json")
    # Exclusive creation prevents overwriting any earlier export.
    with text_path.open("x", encoding="utf-8-sig", newline="") as stream:
        stream.write(render_text(report))
    with json_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    return text_path, json_path


def collect_rows(cdp, count, timeout):
    adapter_call(cdp, "personal")
    wait_until(lambda: adapter_call(cdp, "list"), lambda s: s.get("personal") and bool(s.get("rows")), timeout, "personal chat list")
    adapter_call(cdp, "scroll_list", "top")
    wait_until(lambda: adapter_call(cdp, "list"), lambda s: s.get("scroll_top", 99) < 2, timeout, "list start")
    seen = {}
    previous_end = None
    stagnant = 0
    for _ in range(max(30, count * 3)):
        state = adapter_call(cdp, "list")
        if not state.get("personal"):
            raise AgentError("Personal tab changed during export. Do not use the browser while exporting.")
        for row in state.get("rows", []):
            if row["kind"] != "personal" or row["self"] or row["join_only"]:
                continue
            seen[row["index"]] = row
        rows = sorted(seen.values(), key=lambda r: r["index"])
        unpinned = [r for r in rows if not r["pinned"]]
        # Gather N unpinned contacts plus *all* pinned contacts: pinning is not recency.
        if len(unpinned) >= count:
            return [r for r in rows if r["pinned"]] + unpinned[:count]
        end = (state.get("scroll_top"), tuple(r["index"] for r in state.get("rows", [])))
        stagnant = stagnant + 1 if end == previous_end else 0
        if state.get("at_bottom") or stagnant >= 3:
            return rows
        previous_end = end
        adapter_call(cdp, "scroll_list", "next")
        time.sleep(.18)  # Virtualized list must render a new batch after scrolling.
    raise AgentError("List did not converge; the page layout may have changed.")


def open_row(cdp, row, timeout):
    adapter_call(cdp, "scroll_list", "top")
    for _ in range(max(30, row["index"] // 2 + 15)):
        result = adapter_call(cdp, "open", row)
        if result.get("opened"):
            return
        if result.get("mismatch"):
            raise AgentError("Chat list reordered during export. Retry to obtain a consistent list.")
        if result.get("at_bottom"):
            break
        adapter_call(cdp, "scroll_list", "next")
        time.sleep(.15)
    raise AgentError(f"Could not locate conversation: {row['name']}")


def collect_message(cdp, row, timeout):
    open_row(cdp, row, timeout)
    wait_until(lambda: adapter_call(cdp, "message"),
               lambda s: s.get("name") == row["name"] and not s.get("loading") and s.get("message"),
               timeout, f"message load: {row['name']}")
    adapter_call(cdp, "bottom")
    deadline = time.monotonic() + timeout
    prior = None
    since = time.monotonic()
    while time.monotonic() < deadline:
        state = adapter_call(cdp, "message")
        if state.get("name") != row["name"]:
            raise AgentError("The selected conversation changed during export.")
        message = state.get("message")
        signature = json.dumps(message, ensure_ascii=False, sort_keys=True)
        if signature != prior or state.get("loading") or not state.get("at_bottom"):
            prior, since = signature, time.monotonic()
        if message and time.monotonic() - since >= .65:
            if not message.get("epoch_ms"):
                raise AgentError("Message timestamp is missing; refusing an unverified result.")
            if not message.get("text") and not message.get("media_details") and message.get("kind") == "text":
                raise AgentError("Message content could not be read.")
            return finalize_record(row, message)
        if not state.get("at_bottom") and not state.get("loading"):
            adapter_call(cdp, "bottom")
        time.sleep(.15)
    raise AgentError(f"Newest message did not settle: {row['name']}")


def export(args):
    try:
        target = select_target(endpoint_targets(args.port), args.target_id)
    except OSError as exc:
        raise AgentError("Agent browser is not running. Run start-browser.cmd first.") from exc
    cdp = CDP(target["webSocketDebuggerUrl"], args.timeout)
    report = {"schema_version": 1, "requested_count": args.count, "collected_at": dt.datetime.now(TEHRAN).isoformat(),
              "source": "Bale Web rendered DOM", "complete": False, "messages": [], "errors": []}
    started = time.monotonic()
    try:
        status = adapter_call(cdp, "status")
        if not status.get("logged_in"):
            raise AgentError("Sign in to Bale manually, then run the export again.")
        rows = collect_rows(cdp, args.count, args.timeout)
        if len({r["name"] for r in rows}) != len(rows):
            raise AgentError("Duplicate contact names found. Rename those chats distinctly before export.")
        log(f"Reading {len(rows)} candidate chats (including pinned chats) for {args.count} results...")
        for i, row in enumerate(rows, 1):
            log(f"[{i}/{len(rows)}] {row['name']}")
            try:
                report["messages"].append(collect_message(cdp, row, args.timeout))
            except (AgentError, OSError, TimeoutError) as exc:
                report["errors"].append(f"{row['name']}: {exc}")
                log(f"  Could not verify: {exc}")
        report["messages"].sort(key=lambda m: float(m["epoch_ms"]), reverse=True)
        report["messages"] = report["messages"][:args.count]
        report["complete"] = len(report["messages"]) == args.count and not report["errors"]
        if len(report["messages"]) < args.count:
            report["errors"].append(f"Only {len(report['messages'])} eligible messages were readable.")
    except KeyboardInterrupt:
        report["errors"].append("Stopped by the user; completed records were retained.")
    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        cdp.close()
    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    txt, js = save_report(report, args.output)
    log(f"{'COMPLETE' if report['complete'] else 'PARTIAL'}: {len(report['messages'])} messages in {report['elapsed_seconds']}s")
    log(f"Text: {txt}\nJSON: {js}")
    for error in report["errors"]:
        log(f"Error: {error}")
    return 0 if report["complete"] else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Portable, local-only Bale Web message exporter")
    sub = parser.add_subparsers(dest="command", required=True)
    launch = sub.add_parser("launch", help="Open a dedicated Chrome/Edge profile")
    launch.add_argument("--browser")
    launch.add_argument("--profile")
    launch.add_argument("--port", type=int, default=9222)
    run = sub.add_parser("export", help="Read the newest message in recent personal chats")
    run.add_argument("--count", type=int, default=10)
    run.add_argument("--port", type=int, default=9222)
    run.add_argument("--target-id")
    run.add_argument("--timeout", type=float, default=20)
    run.add_argument("--output", default=str(ROOT / "output"))
    gui = sub.add_parser("gui", help="Start the Web GUI automation interface")
    args = parser.parse_args(argv)
    if getattr(args, "count", 1) < 1 or getattr(args, "count", 1) > 10000:
        parser.error("--count must be between 1 and 10000")
    if getattr(args, "timeout", 20) < 2:
        parser.error("--timeout must be at least 2 seconds")
    try:
        if args.command == "launch":
            launch_browser(args)
            return 0
        if args.command == "gui":
            import web_gui
            web_gui.main()
            return 0
        return export(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
