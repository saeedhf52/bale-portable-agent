"""Generic Automation Engine over CDP for Bale Portable Agent."""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

from bale_agent import CDP, endpoint_targets, select_target, AgentError, log

ROOT = Path(__file__).resolve().parent


def execute_step(cdp: CDP, step: dict, context: dict) -> dict:
    action = step.get("action")
    if action == "navigate":
        url = step.get("url")
        if not url:
            raise AgentError("آدرس URL برای هدایت وارد نشده است.")
        cdp.call("Page.navigate", {"url": url})
        time.sleep(step.get("wait", 2))
        return {"status": "success", "message": f"هدایت به آدرس {url}"}

    elif action == "click":
        selector = step.get("selector")
        if not selector:
            raise AgentError("سلکتور CSS برای کلیک وارد نشده است.")
        expr = f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            el.click();
            return true;
        }})()"""
        found = cdp.evaluate(expr)
        if not found:
            raise AgentError(f"عنصر با سلکتور {selector} پیدا نشد.")
        time.sleep(step.get("wait", 0.5))
        return {"status": "success", "message": f"کلیک روی {selector}"}

    elif action == "type":
        selector = step.get("selector")
        text = step.get("text", "")
        if not selector:
            raise AgentError("سلکتور CSS برای وارد کردن متن وارد نشده است.")
        expr = f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            el.value = {json.dumps(text)};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()"""
        found = cdp.evaluate(expr)
        if not found:
            raise AgentError(f"عنصر با سلکتور {selector} پیدا نشد.")
        return {"status": "success", "message": f"تایپ متن در {selector}"}

    elif action == "wait":
        seconds = float(step.get("seconds", 1))
        time.sleep(seconds)
        return {"status": "success", "message": f"انتظار به مدت {seconds} ثانیه"}

    elif action == "wait_for_element":
        selector = step.get("selector")
        timeout = float(step.get("timeout", 10))
        deadline = time.monotonic() + timeout
        expr = f"!!document.querySelector({json.dumps(selector)})"
        while time.monotonic() < deadline:
            if cdp.evaluate(expr):
                return {"status": "success", "message": f"عنصر {selector} ظاهر شد."}
            time.sleep(0.5)
        raise AgentError(f"زمان انتظار برای عنصر {selector} به پایان رسید.")

    elif action == "evaluate_js":
        code = step.get("code", "")
        res = cdp.evaluate(code)
        return {"status": "success", "result": res, "message": "کد JS با موفقیت اجرا شد."}

    elif action == "bale_export":
        from bale_agent import collect_rows, collect_message, save_report, TEHRAN
        import datetime as dt

        count = int(step.get("count", 10))
        timeout = float(step.get("timeout", 20))

        report = {
            "schema_version": 1,
            "requested_count": count,
            "collected_at": dt.datetime.now(TEHRAN).isoformat(),
            "source": "Bale Web rendered DOM",
            "complete": False,
            "messages": [],
            "errors": [],
        }

        rows = collect_rows(cdp, count, timeout)
        for i, row in enumerate(rows, 1):
            try:
                report["messages"].append(collect_message(cdp, row, timeout))
            except Exception as exc:
                report["errors"].append(f"{row['name']}: {exc}")

        report["messages"].sort(key=lambda m: float(m["epoch_ms"]), reverse=True)
        report["messages"] = report["messages"][:count]
        report["complete"] = len(report["messages"]) == count and not report["errors"]

        txt, js = save_report(report, ROOT / "output")
        return {
            "status": "success",
            "messages_count": len(report["messages"]),
            "txt_path": str(txt),
            "json_path": str(js),
            "message": f"استخراج {len(report['messages'])} پیام انجام شد.",
        }

    else:
        raise AgentError(f"عملیات ناشناخته: {action}")


def run_automation_steps(steps: list[dict], port: int = 9222) -> list[dict]:
    targets = endpoint_targets(port)
    # Find any available page target or fallback to Bale target
    target = None
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            target = t
            break

    if not target:
        raise AgentError("هیچ صفحه مرورگری برای اشکال‌زدایی یافت نشد. ابتدا start-browser.cmd را اجرا کنید.")

    cdp = CDP(target["webSocketDebuggerUrl"], timeout=30)
    results = []
    context = {}
    try:
        for idx, step in enumerate(steps, 1):
            log(f"اجرای گام {idx}: {step.get('action')}")
            res = execute_step(cdp, step, context)
            results.append({"step": idx, "action": step.get("action"), **res})
    finally:
        cdp.close()

    return results
