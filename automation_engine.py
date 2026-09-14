"""Generic CDP Automation Engine — Portable Web Agent."""
from __future__ import annotations

import json
import time
import datetime as dt
from pathlib import Path

from bale_agent import CDP, endpoint_targets, AgentError, log

ROOT = Path(__file__).resolve().parent

# ─── Helpers ───

def _js_q(s):
    """JSON-safe quote for embedding in JS template."""
    return json.dumps(s)


def _ensure(cdp, selector, timeout=10):
    """Wait for selector, return True or raise."""
    expr = f"!!document.querySelector({_js_q(selector)})"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cdp.evaluate(expr):
            return True
        time.sleep(0.4)
    raise AgentError(f"عنصر {selector} در {timeout} ثانیه ظاهر نشد.")


# ─── Action Handlers ───

def _navigate(cdp, step, ctx):
    url = step.get("url", "")
    if not url:
        raise AgentError("آدرس URL وارد نشده است.")
    cdp.call("Page.navigate", {"url": url})
    time.sleep(step.get("wait", 2))
    return {"message": f"هدایت به {url}"}


def _click(cdp, step, ctx):
    sel = step.get("selector", "")
    if not sel:
        raise AgentError("سلکتور CSS وارد نشده است.")
    found = cdp.evaluate(f"""(() => {{
        const el = document.querySelector({_js_q(sel)});
        if (!el) return false;
        el.scrollIntoView({{block:'center'}});
        el.click();
        return true;
    }})()""")
    if not found:
        raise AgentError(f"عنصر {sel} پیدا نشد.")
    time.sleep(step.get("wait", 0.5))
    return {"message": f"کلیک روی {sel}"}


def _type_text(cdp, step, ctx):
    sel = step.get("selector", "")
    text = step.get("text", "")
    # Dynamic text: replace {{var}} with context values
    for key, val in ctx.items():
        text = text.replace("{{" + key + "}}", str(val))
    if not sel:
        raise AgentError("سلکتور CSS وارد نشده است.")
    clear = step.get("clear", True)
    found = cdp.evaluate(f"""(() => {{
        const el = document.querySelector({_js_q(sel)});
        if (!el) return false;
        el.focus();
        if ({json.dumps(clear)}) el.value = '';
        el.value += {_js_q(text)};
        el.dispatchEvent(new Event('input', {{bubbles:true}}));
        el.dispatchEvent(new Event('change', {{bubbles:true}}));
        return true;
    }})()""")
    if not found:
        raise AgentError(f"عنصر {sel} پیدا نشد.")
    return {"message": f"تایپ متن در {sel}"}


def _type_human(cdp, step, ctx):
    """Type character by character with random delays for anti-bot."""
    sel = step.get("selector", "")
    text = step.get("text", "")
    for key, val in ctx.items():
        text = text.replace("{{" + key + "}}", str(val))
    if not sel:
        raise AgentError("سلکتور CSS وارد نشده است.")
    cdp.evaluate(f"""(() => {{
        const el = document.querySelector({_js_q(sel)});
        if (!el) throw new Error('عنصر پیدا نشد');
        el.focus();
        el.value = '';
    }})()""")
    for ch in text:
        cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            el.value += {_js_q(ch)};
            el.dispatchEvent(new Event('input', {{bubbles:true}}));
        }})()""")
        time.sleep(step.get("char_delay", 0.08))
    cdp.evaluate(f"""document.querySelector({_js_q(sel)}).dispatchEvent(new Event('change', {{bubbles:true}}))""")
    return {"message": f"تایپ هوشمند ({len(text)} کاراکتر) در {sel}"}


def _wait(cdp, step, ctx):
    seconds = float(step.get("seconds", 1))
    time.sleep(seconds)
    return {"message": f"انتظار {seconds} ثانیه"}


def _wait_for_element(cdp, step, ctx):
    sel = step.get("selector", "")
    timeout = float(step.get("timeout", 10))
    _ensure(cdp, sel, timeout)
    return {"message": f"عنصر {sel} ظاهر شد."}


def _wait_element_gone(cdp, step, ctx):
    """Wait until an element disappears (e.g. loading spinner)."""
    sel = step.get("selector", "")
    timeout = float(step.get("timeout", 15))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not cdp.evaluate(f"!!document.querySelector({_js_q(sel)})"):
            return {"message": f"عنصر {sel} ناپدید شد."}
        time.sleep(0.4)
    raise AgentError(f"عنصر {sel} در {timeout} ثانیه ناپدید نشد.")


def _wait_for_human(cdp, step, ctx):
    """Pause and wait for human intervention (captcha, 2FA, etc.)."""
    sel = step.get("success_selector", "")
    timeout = float(step.get("timeout", 120))
    prompt_msg = step.get("prompt", "لطفاً عملیات دستی (مثلاً کپچا) را انجام دهید...")
    log(f"⏸️  انتظار دخالت کاربر: {prompt_msg}")
    # Inject a visible banner on the page
    cdp.evaluate(f"""(() => {{
        if (document.getElementById('__agent_human_wait')) return;
        const d = document.createElement('div');
        d.id = '__agent_human_wait';
        d.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:16px;background:#f59e0b;color:#000;text-align:center;font-size:16px;font-weight:bold;z-index:999999;direction:rtl;font-family:Tahoma';
        d.textContent = {_js_q(prompt_msg)};
        document.body.prepend(d);
    }})()""")
    deadline = time.monotonic() + timeout
    if sel:
        while time.monotonic() < deadline:
            if cdp.evaluate(f"!!document.querySelector({_js_q(sel)})"):
                cdp.evaluate("document.getElementById('__agent_human_wait')?.remove()")
                return {"message": "دخالت کاربر تکمیل شد."}
            time.sleep(1)
        cdp.evaluate("document.getElementById('__agent_human_wait')?.remove()")
        raise AgentError(f"زمان انتظار دخالت کاربر ({timeout}s) به پایان رسید.")
    else:
        time.sleep(timeout)
        cdp.evaluate("document.getElementById('__agent_human_wait')?.remove()")
        return {"message": f"انتظار {timeout} ثانیه برای دخالت کاربر سپری شد."}


def _evaluate_js(cdp, step, ctx):
    code = step.get("code", "")
    res = cdp.evaluate(code)
    if step.get("store_as"):
        ctx[step["store_as"]] = res
    return {"result": res, "message": "کد JS اجرا شد."}


def _extract_text(cdp, step, ctx):
    """Extract text content of an element and optionally store in context."""
    sel = step.get("selector", "")
    attr = step.get("attribute", "")
    expr = f"""(() => {{
        const el = document.querySelector({_js_q(sel)});
        if (!el) return null;
        return {f'el.getAttribute({_js_q(attr)})' if attr else 'el.textContent.trim()'};
    }})()"""
    val = cdp.evaluate(expr)
    if val is None:
        raise AgentError(f"عنصر {sel} پیدا نشد.")
    store = step.get("store_as", "")
    if store:
        ctx[store] = val
    return {"result": val, "message": f"متن استخراج شد: {str(val)[:80]}"}


def _extract_list(cdp, step, ctx):
    """Extract text from all matching elements into a list."""
    sel = step.get("selector", "")
    attr = step.get("attribute", "")
    expr = f"""(() => {{
        const els = document.querySelectorAll({_js_q(sel)});
        return Array.from(els).map(el => {f'el.getAttribute({_js_q(attr)})' if attr else 'el.textContent.trim()'});
    }})()"""
    val = cdp.evaluate(expr) or []
    store = step.get("store_as", "extracted_list")
    ctx[store] = val
    return {"result": val, "message": f"لیست استخراج شد ({len(val)} مورد)"}


def _scroll(cdp, step, ctx):
    """Scroll page or element."""
    sel = step.get("selector", "")
    direction = step.get("direction", "down")
    amount = int(step.get("amount", 500))
    dy = amount if direction == "down" else -amount
    if sel:
        cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            if (el) el.scrollBy(0, {dy});
        }})()""")
    else:
        cdp.evaluate(f"window.scrollBy(0, {dy})")
    time.sleep(step.get("wait", 0.5))
    return {"message": f"اسکرول {'پایین' if direction == 'down' else 'بالا'} ({amount}px)"}


def _scroll_to_bottom(cdp, step, ctx):
    """Incrementally scroll to bottom of page/element, collecting items."""
    sel = step.get("selector", "")
    max_scrolls = int(step.get("max_scrolls", 20))
    wait = float(step.get("wait", 1))
    for _ in range(max_scrolls):
        if sel:
            at_end = cdp.evaluate(f"""(() => {{
                const el = document.querySelector({_js_q(sel)});
                if (!el) return true;
                el.scrollBy(0, el.clientHeight);
                return el.scrollHeight - el.scrollTop - el.clientHeight < 5;
            }})()""")
        else:
            at_end = cdp.evaluate("""(() => {
                window.scrollBy(0, window.innerHeight);
                return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 5;
            })()""")
        time.sleep(wait)
        if at_end:
            break
    return {"message": "پیمایش تا انتهای صفحه/لیست انجام شد."}


def _crawl_links(cdp, step, ctx):
    """Collect all links matching a selector."""
    sel = step.get("selector", "a[href]")
    expr = f"""(() => {{
        return Array.from(document.querySelectorAll({_js_q(sel)})).map(a => ({{
            text: a.textContent.trim().slice(0, 100),
            href: a.href || a.getAttribute('href') || ''
        }}));
    }})()"""
    links = cdp.evaluate(expr) or []
    store = step.get("store_as", "crawled_links")
    ctx[store] = links
    return {"result": links, "message": f"جمع‌آوری {len(links)} لینک"}


def _screenshot(cdp, step, ctx):
    """Take a screenshot and save to output folder."""
    import base64
    result = cdp.call("Page.captureScreenshot", {"format": "png"})
    data = base64.b64decode(result.get("data", ""))
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    fname = f"screenshot_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = out / fname
    path.write_bytes(data)
    return {"message": f"اسکرین‌شات ذخیره شد: {fname}", "path": str(path)}


def _select_option(cdp, step, ctx):
    """Select an option from a <select> dropdown."""
    sel = step.get("selector", "")
    value = step.get("value", "")
    found = cdp.evaluate(f"""(() => {{
        const el = document.querySelector({_js_q(sel)});
        if (!el) return false;
        el.value = {_js_q(value)};
        el.dispatchEvent(new Event('change', {{bubbles:true}}));
        return true;
    }})()""")
    if not found:
        raise AgentError(f"عنصر select با سلکتور {sel} پیدا نشد.")
    return {"message": f"انتخاب گزینه {value} در {sel}"}


def _set_variable(cdp, step, ctx):
    """Set a context variable for use in dynamic text templates."""
    key = step.get("key", "")
    value = step.get("value", "")
    if not key:
        raise AgentError("نام متغیر (key) وارد نشده.")
    ctx[key] = value
    return {"message": f"متغیر {key} تنظیم شد."}


def _loop(cdp, step, ctx):
    """Run sub-steps multiple times."""
    count = int(step.get("count", 1))
    sub_steps = step.get("steps", [])
    results = []
    for i in range(count):
        ctx["loop_index"] = i
        for sub in sub_steps:
            r = execute_step(cdp, sub, ctx)
            results.append(r)
    return {"message": f"حلقه {count} بار اجرا شد ({len(results)} گام)", "sub_results": results}


def _conditional(cdp, step, ctx):
    """Run sub-steps only if a selector exists."""
    sel = step.get("selector", "")
    exists = cdp.evaluate(f"!!document.querySelector({_js_q(sel)})")
    sub_steps = step.get("then_steps" if exists else "else_steps", [])
    results = []
    for sub in sub_steps:
        r = execute_step(cdp, sub, ctx)
        results.append(r)
    branch = "then" if exists else "else"
    return {"message": f"شرط ({sel}): شاخه {branch} اجرا شد.", "sub_results": results}


def _bale_export(cdp, step, ctx):
    from bale_agent import collect_rows, collect_message, save_report, TEHRAN

    count = int(step.get("count", 10))
    timeout = float(step.get("timeout", 20))

    report = {
        "schema_version": 1, "requested_count": count,
        "collected_at": dt.datetime.now(TEHRAN).isoformat(),
        "source": "Bale Web rendered DOM", "complete": False,
        "messages": [], "errors": [],
    }
    rows = collect_rows(cdp, count, timeout)
    for row in rows:
        try:
            report["messages"].append(collect_message(cdp, row, timeout))
        except Exception as exc:
            report["errors"].append(f"{row['name']}: {exc}")
    report["messages"].sort(key=lambda m: float(m["epoch_ms"]), reverse=True)
    report["messages"] = report["messages"][:count]
    report["complete"] = len(report["messages"]) == count and not report["errors"]
    txt, js = save_report(report, ROOT / "output")
    return {"message": f"استخراج {len(report['messages'])} پیام انجام شد.", "txt_path": str(txt), "json_path": str(js)}


# ─── Action Registry ───

ACTIONS = {
    "navigate":         _navigate,
    "click":            _click,
    "type":             _type_text,
    "type_human":       _type_human,
    "wait":             _wait,
    "wait_for_element": _wait_for_element,
    "wait_element_gone":_wait_element_gone,
    "wait_for_human":   _wait_for_human,
    "evaluate_js":      _evaluate_js,
    "extract_text":     _extract_text,
    "extract_list":     _extract_list,
    "scroll":           _scroll,
    "scroll_to_bottom": _scroll_to_bottom,
    "crawl_links":      _crawl_links,
    "screenshot":       _screenshot,
    "select_option":    _select_option,
    "set_variable":     _set_variable,
    "loop":             _loop,
    "conditional":      _conditional,
    "bale_export":      _bale_export,
}


def execute_step(cdp: CDP, step: dict, context: dict) -> dict:
    action = step.get("action")
    handler = ACTIONS.get(action)
    if not handler:
        raise AgentError(f"عملیات ناشناخته: {action}")
    result = handler(cdp, step, context)
    result["status"] = "success"
    return result


def run_automation_steps(steps: list[dict], port: int = 9222) -> list[dict]:
    targets = endpoint_targets(port)
    target = None
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            target = t
            break
    if not target:
        raise AgentError("مرورگری برای اشکال‌زدایی یافت نشد. ابتدا start-browser.cmd را اجرا کنید.")

    cdp = CDP(target["webSocketDebuggerUrl"], timeout=30)
    results = []
    context = {}
    try:
        for idx, step in enumerate(steps, 1):
            log(f"گام {idx}: {step.get('action')}")
            res = execute_step(cdp, step, context)
            results.append({"step": idx, "action": step.get("action"), **res})
    finally:
        cdp.close()
    return results


# ─── Built-in Templates ───

TEMPLATES = {
    "login_basic": {
        "name": "ورود به سایت (عمومی)",
        "description": "هدایت به صفحه ورود، وارد کردن نام کاربری و رمز، کلیک روی دکمه ورود",
        "steps": [
            {"action": "navigate", "url": "https://example.com/login", "wait": 2},
            {"action": "type", "selector": "#username", "text": ""},
            {"action": "type", "selector": "#password", "text": ""},
            {"action": "click", "selector": "button[type=submit]", "wait": 3},
            {"action": "wait_for_element", "selector": ".dashboard", "timeout": 10},
        ]
    },
    "login_captcha": {
        "name": "ورود با کپچا (انتظار دستی)",
        "description": "ورود به سایت دارای کپچا — بعد از وارد کردن اطلاعات، منتظر حل کپچا توسط کاربر می‌ماند",
        "steps": [
            {"action": "navigate", "url": "https://example.com/login", "wait": 2},
            {"action": "type", "selector": "#username", "text": ""},
            {"action": "type", "selector": "#password", "text": ""},
            {"action": "wait_for_human", "prompt": "لطفاً کپچا را حل کنید و دکمه ورود را بزنید.", "success_selector": ".dashboard", "timeout": 120},
        ]
    },
    "crawl_page": {
        "name": "جمع‌آوری لینک‌های صفحه",
        "description": "هدایت به صفحه و جمع‌آوری تمام لینک‌ها",
        "steps": [
            {"action": "navigate", "url": "https://example.com", "wait": 3},
            {"action": "crawl_links", "selector": "a[href]", "store_as": "links"},
        ]
    },
    "scroll_and_extract": {
        "name": "پیمایش لیست و استخراج آیتم‌ها",
        "description": "اسکرول تا انتهای لیست و استخراج متن تمام آیتم‌ها",
        "steps": [
            {"action": "navigate", "url": "https://example.com/list", "wait": 3},
            {"action": "scroll_to_bottom", "max_scrolls": 15, "wait": 1},
            {"action": "extract_list", "selector": ".list-item", "store_as": "items"},
        ]
    },
    "form_fill_dynamic": {
        "name": "پر کردن فرم با متغیرهای داینامیک",
        "description": "تنظیم متغیرها و پر کردن فرم با مقادیر پویا",
        "steps": [
            {"action": "set_variable", "key": "user", "value": "admin"},
            {"action": "set_variable", "key": "pass", "value": "123456"},
            {"action": "navigate", "url": "https://example.com/form", "wait": 2},
            {"action": "type", "selector": "#username", "text": "{{user}}"},
            {"action": "type_human", "selector": "#password", "text": "{{pass}}", "char_delay": 0.1},
            {"action": "click", "selector": "button[type=submit]", "wait": 2},
        ]
    },
    "bale_export": {
        "name": "استخراج پیام‌های اخیر بله",
        "description": "استخراج آخرین پیام از مخاطبان شخصی اخیر بله",
        "steps": [
            {"action": "bale_export", "count": 10, "timeout": 20},
        ]
    },
}
