"""Generic CDP Automation Engine — Portable Web Agent."""
from __future__ import annotations

import json
import time
import datetime as dt
from pathlib import Path

from bale_agent import CDP, endpoint_targets, AgentError, log, ensure_browser_ready

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
    time.sleep(_to_float(step.get("wait"), 2.0))
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
    time.sleep(_to_float(step.get("wait"), 0.5))
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
        time.sleep(_to_float(step.get("char_delay"), 0.08))
    cdp.evaluate(f"""document.querySelector({_js_q(sel)}).dispatchEvent(new Event('change', {{bubbles:true}}))""")
    return {"message": f"تایپ هوشمند ({len(text)} کاراکتر) در {sel}"}


def _wait(cdp, step, ctx):
    seconds = _to_float(step.get("seconds"), 1.0)
    time.sleep(seconds)
    return {"message": f"انتظار {seconds} ثانیه"}


def _wait_for_element(cdp, step, ctx):
    sel = step.get("selector", "")
    timeout = _to_float(step.get("timeout"), 10.0)
    _ensure(cdp, sel, timeout)
    return {"message": f"عنصر {sel} ظاهر شد."}


def _wait_element_gone(cdp, step, ctx):
    """Wait until an element disappears (e.g. loading spinner)."""
    sel = step.get("selector", "")
    timeout = _to_float(step.get("timeout"), 15.0)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not cdp.evaluate(f"!!document.querySelector({_js_q(sel)})"):
            return {"message": f"عنصر {sel} ناپدید شد."}
        time.sleep(0.4)
    raise AgentError(f"عنصر {sel} در {timeout} ثانیه ناپدید نشد.")


def _wait_for_human(cdp, step, ctx):
    """Pause and wait for human intervention (captcha, 2FA, etc.)."""
    sel = step.get("success_selector", "")
    timeout = _to_float(step.get("timeout"), 120.0)
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
    amount = _to_int(step.get("amount"), 500)
    dy = amount if direction == "down" else -amount
    if sel:
        cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            if (el) el.scrollBy(0, {dy});
        }})()""")
    else:
        cdp.evaluate(f"window.scrollBy(0, {dy})")
    time.sleep(_to_float(step.get("wait"), 0.5))
    return {"message": f"اسکرول {'پایین' if direction == 'down' else 'بالا'} ({amount}px)"}


def _scroll_to_bottom(cdp, step, ctx):
    """Incrementally scroll to bottom of page/element, collecting items."""
    sel = step.get("selector", "")
    max_scrolls = _to_int(step.get("max_scrolls"), 20)
    wait = _to_float(step.get("wait"), 1.0)
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
    """Run sub-steps multiple times, with optional break_if / continue_if conditions."""
    count = _to_int(step.get("count"), 1)
    sub_steps = step.get("steps", [])
    break_if = step.get("break_if", "")
    continue_if = step.get("continue_if", "")
    results = []
    for i in range(count):
        ctx["loop_index"] = i
        # Break condition: stop loop if element exists
        if break_if and _eval_condition(cdp, {"type": "selector_exists", "selector": break_if}, ctx):
            log(f"🔁 حلقه در تکرار {i} متوقف شد (break_if: {break_if})")
            break
        # Continue condition: skip iteration if element exists
        if continue_if and _eval_condition(cdp, {"type": "selector_exists", "selector": continue_if}, ctx):
            log(f"🔁 تکرار {i} رد شد (continue_if: {continue_if})")
            continue
        for sub in sub_steps:
            r = execute_step(cdp, sub, ctx)
            results.append(r)
    return {"message": f"حلقه {count} بار اجرا شد ({len(results)} گام)", "sub_results": results}


def _eval_condition(cdp, cond, ctx):
    """Evaluate a single condition dict and return bool.

    Supported condition types:
      selector_exists  — element found in DOM
      selector_visible — element visible on page
      selector_gone    — element NOT in DOM
      text_contains    — element text contains value
      text_equals      — element text equals value
      url_contains     — current URL contains value
      url_equals       — current URL equals value
      variable_equals  — context variable equals value
      variable_set     — context variable is truthy
      js_expression    — arbitrary JS returns truthy
    """
    ctype = cond.get("type", "selector_exists")
    sel = cond.get("selector", "")
    value = cond.get("value", "")
    var_key = cond.get("variable", "")

    # Replace {{var}} in selector and value
    for k, v in ctx.items():
        sel = sel.replace("{{" + str(k) + "}}", str(v))
        value = value.replace("{{" + str(k) + "}}", str(v))

    if ctype == "selector_exists":
        return bool(cdp.evaluate(f"!!document.querySelector({_js_q(sel)})"))

    elif ctype == "selector_visible":
        return bool(cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            return el && el.offsetParent !== null;
        }})()"""))

    elif ctype == "selector_gone":
        return not bool(cdp.evaluate(f"!!document.querySelector({_js_q(sel)})"))

    elif ctype == "text_contains":
        text = cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            return el ? el.textContent.trim() : '';
        }})()""") or ""
        return value.lower() in text.lower()

    elif ctype == "text_equals":
        text = cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(sel)});
            return el ? el.textContent.trim() : '';
        }})()""") or ""
        return text.strip() == value.strip()

    elif ctype == "url_contains":
        url = cdp.evaluate("window.location.href") or ""
        return value in url

    elif ctype == "url_equals":
        url = cdp.evaluate("window.location.href") or ""
        return url.strip() == value.strip()

    elif ctype == "variable_equals":
        return str(ctx.get(var_key, "")) == value

    elif ctype == "variable_set":
        return bool(ctx.get(var_key))

    elif ctype == "js_expression":
        code = cond.get("code", value)
        return bool(cdp.evaluate(code))

    else:
        log(f"⚠️ نوع شرط ناشناخته: {ctype}")
        return False


def _eval_conditions(cdp, conditions, logic, ctx):
    """Evaluate a list of conditions with AND/OR logic."""
    if not conditions:
        return True
    results = [_eval_condition(cdp, c, ctx) for c in conditions]
    if logic == "or":
        return any(results)
    return all(results)  # default: and


def _conditional(cdp, step, ctx):
    """Smart conditional with multiple condition types, operators, and nested branches.

    Simple mode (backward compatible):
      {"action": "conditional", "selector": ".error", "then_steps": [...], "else_steps": [...]}

    Advanced mode:
      {"action": "conditional",
       "conditions": [
         {"type": "selector_exists", "selector": ".error-msg"},
         {"type": "url_contains", "value": "/dashboard"}
       ],
       "logic": "and",  // "and" | "or"
       "negate": false,  // flip result
       "then_steps": [...],
       "else_steps": [...]}
    """
    # Simple mode: single selector
    sel = step.get("selector", "")
    conditions = step.get("conditions", [])

    if not conditions and sel:
        # Backward-compatible: single selector_exists
        conditions = [{"type": "selector_exists", "selector": sel}]

    logic = step.get("logic", "and")
    negate = step.get("negate", False)

    result = _eval_conditions(cdp, conditions, logic, ctx)
    if negate:
        result = not result

    branch = "then" if result else "else"
    sub_steps = step.get("then_steps" if result else "else_steps", [])

    # Log condition evaluation
    cond_desc = sel if sel else f"{len(conditions)} شرط ({logic})"
    log(f"❓ شرط [{cond_desc}]: نتیجه={'✅ صحیح' if result else '❌ ناصحیح'} → شاخه {branch}")

    results = []
    for sub in sub_steps:
        r = execute_step(cdp, sub, ctx)
        results.append(r)
    return {"message": f"شرط ({cond_desc}): شاخه {branch} اجرا شد.", "sub_results": results, "condition_result": result}


def _while_loop(cdp, step, ctx):
    """Loop while condition(s) remain true — smart while loop.

    {"action": "while_loop",
     "conditions": [{"type": "selector_exists", "selector": ".next-btn"}],
     "logic": "and",
     "max_iterations": 100,
     "steps": [...]}
    """
    conditions = step.get("conditions", [])
    sel = step.get("selector", "")
    if not conditions and sel:
        conditions = [{"type": "selector_exists", "selector": sel}]

    logic = step.get("logic", "and")
    max_iter = _to_int(step.get("max_iterations"), 100)
    sub_steps = step.get("steps", [])
    results = []
    iteration = 0

    while iteration < max_iter:
        if not _eval_conditions(cdp, conditions, logic, ctx):
            log(f"🔄 while_loop: شرط ناصحیح شد — پایان در تکرار {iteration}")
            break
        ctx["loop_index"] = iteration
        for sub in sub_steps:
            r = execute_step(cdp, sub, ctx)
            results.append(r)
        iteration += 1

    return {"message": f"حلقه شرطی {iteration} بار اجرا شد ({len(results)} گام)", "sub_results": results}


def _try_catch(cdp, step, ctx):
    """Try-catch block for error handling in automation flow.

    {"action": "try_catch",
     "try_steps": [...],
     "catch_steps": [...],
     "finally_steps": [...]}
    """
    try_steps = step.get("try_steps", [])
    catch_steps = step.get("catch_steps", [])
    finally_steps = step.get("finally_steps", [])
    results = []
    error_occurred = False
    error_msg = ""

    try:
        for sub in try_steps:
            r = execute_step(cdp, sub, ctx)
            results.append(r)
    except Exception as exc:
        error_occurred = True
        error_msg = str(exc)
        ctx["_error"] = error_msg
        log(f"⚠️ try_catch: خطا رخ داد — {error_msg}")
        for sub in catch_steps:
            try:
                r = execute_step(cdp, sub, ctx)
                results.append(r)
            except Exception as inner_exc:
                log(f"❌ خطا در catch: {inner_exc}")

    # Finally always runs
    for sub in finally_steps:
        try:
            r = execute_step(cdp, sub, ctx)
            results.append(r)
        except Exception as fin_exc:
            log(f"❌ خطا در finally: {fin_exc}")

    status = "خطا (مدیریت شده)" if error_occurred else "موفق"
    return {"message": f"try_catch: {status}", "sub_results": results, "error": error_msg if error_occurred else None}


def _detect_login(cdp, step, ctx):
    """Detect login form fields on the current page automatically."""
    result = cdp.evaluate("""(() => {
        const selectors = {
            username: [
                'input[name="username"]', 'input[name="user"]', 'input[name="login"]',
                'input[name="email"]', 'input[type="email"]', 'input[name="userid"]',
                'input[name="user_name"]', 'input[name="loginId"]', 'input[name="account"]',
                'input[id*="user" i]', 'input[id*="login" i]', 'input[id*="email" i]',
                'input[id*="account" i]', 'input[id*="mobile" i]', 'input[id*="phone" i]',
                'input[placeholder*="نام کاربری" i]', 'input[placeholder*="ایمیل" i]',
                'input[placeholder*="شماره" i]', 'input[placeholder*="موبایل" i]',
                'input[placeholder*="username" i]', 'input[placeholder*="email" i]',
                'input[placeholder*="phone" i]', 'input[placeholder*="mobile" i]',
                'input[autocomplete="username"]', 'input[autocomplete="email"]',
                'input[type="text"]:not([name*="search" i]):not([name*="query" i])',
                'input[type="tel"]',
            ],
            password: [
                'input[type="password"]',
                'input[name="password"]', 'input[name="pass"]', 'input[name="passwd"]',
                'input[name="pwd"]', 'input[id*="pass" i]', 'input[id*="pwd" i]',
                'input[placeholder*="رمز" i]', 'input[placeholder*="گذرواژه" i]',
                'input[placeholder*="password" i]',
                'input[autocomplete="current-password"]',
            ],
            submit: [
                'button[type="submit"]', 'input[type="submit"]',
                'button[id*="login" i]', 'button[id*="signin" i]', 'button[id*="submit" i]',
                'button[class*="login" i]', 'button[class*="signin" i]', 'button[class*="submit" i]',
                'a[id*="login" i]', 'a[class*="login" i]',
                'button:not([type="button"]):not([type="reset"])',
                '[role="button"][class*="login" i]', '[role="button"][class*="submit" i]',
            ],
            captcha: [
                'iframe[src*="recaptcha"]', 'iframe[src*="captcha"]',
                'div[class*="captcha" i]', 'div[id*="captcha" i]',
                'img[src*="captcha" i]', 'input[name*="captcha" i]',
                'div[class*="g-recaptcha"]', '.h-captcha',
            ],
            success: [
                '.dashboard', '.profile', '.home', '.main-content',
                '[class*="dashboard" i]', '[class*="profile" i]', '[id*="dashboard" i]',
                '[class*="welcome" i]', '[class*="logout" i]', 'a[href*="logout" i]',
                'button[class*="logout" i]', '[id*="user-menu" i]', '[class*="user-menu" i]',
            ],
        };
        const find = (list) => {
            for (const s of list) {
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) return s;
            }
            return null;
        };
        const result = {
            username_selector: find(selectors.username),
            password_selector: find(selectors.password),
            submit_selector: find(selectors.submit),
            has_captcha: find(selectors.captcha) !== null,
            captcha_selector: find(selectors.captcha),
            success_selector: find(selectors.success),
            is_login_page: false,
            page_title: document.title,
            page_url: location.href,
        };
        // A page is a login page if it has at least a password field or (username + submit)
        result.is_login_page = !!(result.password_selector || (result.username_selector && result.submit_selector));
        return result;
    })()""")
    if step.get("store_as"):
        ctx[step["store_as"]] = result
    return {"result": result, "message": f"تشخیص فرم: {'صفحه ورود یافت شد ✅' if result.get('is_login_page') else 'صفحه ورود یافت نشد ❌'}"}


def _auto_login(cdp, step, ctx):
    """Smart login: detect form, fill credentials, handle captcha, verify success."""
    url = step.get("url", "")
    username = step.get("username", "")
    password = step.get("password", "")
    timeout = _to_float(step.get("timeout"), 30.0)
    human_on_captcha = step.get("human_on_captcha", True)

    # Replace {{var}} placeholders
    for key, val in ctx.items():
        username = username.replace("{{" + key + "}}", str(val))
        password = password.replace("{{" + key + "}}", str(val))

    # Step 1: Navigate if URL given
    if url:
        cdp.call("Page.navigate", {"url": url})
        time.sleep(_to_float(step.get("wait"), 3.0))

    # Step 2: Wait for page to stabilize
    time.sleep(1)

    # Step 3: Detect login form
    detect_result = _detect_login(cdp, {"store_as": "_login_info"}, ctx)
    info = ctx.get("_login_info", {})

    if not info.get("is_login_page"):
        # Maybe already logged in?
        if info.get("success_selector"):
            return {"message": "قبلاً وارد شده‌اید. ✅", "already_logged_in": True}
        # Try waiting a bit for page load
        time.sleep(2)
        detect_result = _detect_login(cdp, {"store_as": "_login_info"}, ctx)
        info = ctx.get("_login_info", {})
        if not info.get("is_login_page"):
            raise AgentError(f"صفحه ورود تشخیص داده نشد. URL: {info.get('page_url', '?')}")

    results = [f"صفحه ورود یافت شد: {info.get('page_title', '')}"]

    # Step 4: Fill username
    user_sel = step.get("username_selector") or info.get("username_selector")
    if user_sel and username:
        use_human = step.get("human_type", False)
        if use_human:
            _type_human(cdp, {"selector": user_sel, "text": username, "char_delay": step.get("char_delay", 0.06)}, ctx)
        else:
            _type_text(cdp, {"selector": user_sel, "text": username, "clear": True}, ctx)
        results.append(f"نام کاربری وارد شد در {user_sel}")
        time.sleep(0.3)

    # Step 5: Fill password
    pass_sel = step.get("password_selector") or info.get("password_selector")
    if pass_sel and password:
        _type_human(cdp, {"selector": pass_sel, "text": password, "char_delay": step.get("char_delay", 0.05)}, ctx)
        results.append(f"رمز عبور وارد شد در {pass_sel}")
        time.sleep(0.3)

    # Step 6: Handle CAPTCHA
    if info.get("has_captcha") and human_on_captcha:
        results.append("کپچا تشخیص داده شد — در انتظار دخالت کاربر...")
        _wait_for_human(cdp, {
            "prompt": "🔒 کپچا تشخیص داده شد. لطفاً کپچا را حل کنید و سپس دکمه ورود را بزنید.",
            "success_selector": info.get("success_selector", ""),
            "timeout": step.get("captcha_timeout", 120),
        }, ctx)
        results.append("دخالت کاربر تکمیل شد.")
        return {"message": " | ".join(results), "login_info": info}

    # Step 7: Click submit
    submit_sel = step.get("submit_selector") or info.get("submit_selector")
    if submit_sel:
        time.sleep(0.5)
        _click(cdp, {"selector": submit_sel, "wait": 2}, ctx)
        results.append(f"دکمه ورود کلیک شد: {submit_sel}")

    # Step 8: Wait for success / error
    success_sel = step.get("success_selector") or info.get("success_selector", "")
    if success_sel:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Check for success
            if cdp.evaluate(f"!!document.querySelector({_js_q(success_sel)})"):
                results.append("ورود موفقیت‌آمیز ✅")
                return {"message": " | ".join(results), "success": True, "login_info": info}
            # Check for error messages
            error_text = cdp.evaluate("""(() => {
                const errSels = ['.error', '.alert-danger', '.error-message', '[class*="error" i]',
                    '[class*="alert" i]:not(.alert-success)', '.text-danger', '.invalid-feedback',
                    '[role="alert"]', '.notification-error'];
                for (const s of errSels) {
                    const el = document.querySelector(s);
                    if (el && el.textContent.trim() && el.offsetParent !== null) return el.textContent.trim().slice(0, 200);
                }
                return null;
            })()""")
            if error_text:
                results.append(f"خطای ورود: {error_text}")
                return {"message": " | ".join(results), "success": False, "error": error_text, "login_info": info}
            time.sleep(0.5)
        results.append("زمان انتظار تمام شد — وضعیت ورود نامشخص")
    else:
        time.sleep(3)
        results.append("فرآیند ورود تکمیل شد (بدون سلکتور موفقیت)")

    return {"message": " | ".join(results), "login_info": info}


def _scrape_table(cdp, step, ctx):
    """Smart table detection and data extraction from current page."""
    table_sel = step.get("table_selector", "")
    include_hidden = step.get("include_hidden", False)
    store = step.get("store_as", "table_data")

    js = f"""(() => {{
        const tSel = {_js_q(table_sel)};
        const includeHidden = {json.dumps(include_hidden)};

        // ── Find table element ──
        function findTable() {{
            if (tSel) {{
                const el = document.querySelector(tSel);
                if (el) {{
                    if (el.tagName === 'TABLE') return el;
                    const childT = el.querySelector('table');
                    if (childT) return childT;
                    const parentGrid = el.closest('.k-grid, .jarviswidget, [id*="grid" i]');
                    if (parentGrid) {{
                        const gT = parentGrid.querySelector('.k-grid-content table, table[role="treegrid"], table[role="grid"], table');
                        if (gT) return gT;
                    }}
                    return el;
                }}
            }}
            // Kendo Grid — target content table first so rows are present
            let t = document.querySelector('.k-grid-content table, .k-grid table.k-selectable, .k-grid table[role="treegrid"], .k-grid table[role="grid"], #LetterIndex table');
            if (t) return t;
            // Bootstrap / generic data table
            t = document.querySelector('table.table, table.dataTable, table.display, table[id]');
            if (t) return t;
            // Any visible table with >1 row
            const all = document.querySelectorAll('table');
            for (const tb of all) {{
                if (tb.rows.length > 1 && tb.offsetParent !== null) return tb;
            }}
            return null;
        }}

        // ── Find header row ──
        function getHeaders(table) {{
            // Try thead first
            let hdrRow = table.querySelector('thead tr');
            // Kendo separate header table
            if (!hdrRow) {{
                const grid = table.closest('.k-grid, .jarviswidget, [id*="grid" i]');
                if (grid) hdrRow = grid.querySelector('.k-grid-header thead tr, thead tr');
            }}
            if (!hdrRow) return [];
            const cols = [];
            const cells = hdrRow.querySelectorAll('th');
            cells.forEach((th, i) => {{
                const isExplicitHidden = th.style.display === 'none' || th.classList.contains('k-hide');
                const vis = includeHidden || !isExplicitHidden;
                cols.push({{
                    index: i,
                    text: th.textContent.trim().replace(/\\s+/g, ' '),
                    field: th.getAttribute('data-field') || '',
                    visible: vis,
                }});
            }});
            return cols;
        }}

        // ── Extract rows ──
        function getRows(table, headers) {{
            let visIdx = (headers && headers.length > 0) ? new Set(headers.filter(h => h.visible).map(h => h.index)) : null;
            // Fallback: if all headers filtered out as invisible, do not drop all cells
            if (visIdx && visIdx.size === 0) visIdx = null;

            // If selected table is header table (0 data rows), target content table in parent grid
            let dataTable = table;
            if (dataTable.querySelectorAll('td').length === 0) {{
                const grid = dataTable.closest('.k-grid, .jarviswidget, [id*="grid" i]');
                if (grid) {{
                    const contentT = grid.querySelector('.k-grid-content table, table.k-selectable');
                    if (contentT) dataTable = contentT;
                }}
            }}

            const body = dataTable.querySelector('tbody') || dataTable;
            const dataRows = [];
            const allTrs = body.querySelectorAll('tr');
            allTrs.forEach(tr => {{
                // Skip group/header rows
                if (tr.classList.contains('k-grouping-row')) return;
                if (tr.querySelector('th')) return;
                // Must be data row
                const cells = tr.querySelectorAll('td');
                if (cells.length === 0) return;
                const row = {{}};
                let hasData = false;
                cells.forEach((td, i) => {{
                    if (visIdx && !includeHidden && !visIdx.has(i)) return;
                    const hdr = headers.find(h => h.index === i);
                    let key = (hdr && (hdr.field || hdr.text)) || ('col_' + (i + 1));
                    if (!key || key === '\\u00a0' || key.trim() === '') key = 'col_' + (i + 1);
                    let val = td.textContent.trim().replace(/\\s+/g, ' ');
                    // Try to get link href
                    const link = td.querySelector('a[href]');
                    if (link && link.href && !link.href.startsWith('javascript:')) {{
                        row[key + '_link'] = link.href;
                    }}
                    if (val) hasData = true;
                    row[key] = val;
                }});
                if (hasData) dataRows.push(row);
            }});
            return dataRows;
        }}

        // ── Pagination info ──
        function getPaginationInfo() {{
            // Kendo pager
            let pager = document.querySelector('.k-pager-wrap .k-pager-info');
            const info = {{ current_page: 1, total_pages: 1, total_items: 0,
                next_selector: null, prev_selector: null }};
            // Custom: #TotalPages / #TotalLetters
            const tp = document.querySelector('#TotalPages');
            const tl = document.querySelector('#TotalLetters');
            if (tp) info.total_pages = parseInt(tp.textContent) || 1;
            if (tl) info.total_items = parseInt(tl.textContent) || 0;
            // Kendo page numbers
            const selected = document.querySelector('.k-pager-numbers .k-state-selected, .k-pager-numbers li.k-current-page + li .k-state-selected');
            if (selected) info.current_page = parseInt(selected.textContent) || 1;
            // Next button selectors (priority order)
            const nextSels = [
                '#GoNextPage:not([disabled])',
                '.k-pager-nav .k-i-arrow-60-right',
                'a.k-pager-nav[data-page]:not(.k-state-disabled)',
                '.k-pager-nav:not(.k-state-disabled) .k-i-arrow-60-right',
                'a[title*="بعدی"]:not([disabled])',
                'a[title*="next" i]:not([disabled])',
                '.pagination .next:not(.disabled) a',
                'li.next:not(.disabled) a',
                'a.next-page', 'button.next-page',
            ];
            for (const s of nextSels) {{
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) {{
                    info.next_selector = s;
                    break;
                }}
            }}
            const prevSels = [
                '#GoPrevPage:not([disabled])',
                '.k-pager-nav:not(.k-state-disabled) .k-i-arrow-60-left',
            ];
            for (const s of prevSels) {{
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) {{
                    info.prev_selector = s;
                    break;
                }}
            }}
            return info;
        }}

        const table = findTable();
        if (!table) return {{ error: 'جدولی در صفحه یافت نشد.', rows: [], headers: [], pagination: {{}} }};
        const headers = getHeaders(table);
        const rows = getRows(table, headers);
        const pagination = getPaginationInfo();
        return {{
            headers: headers.filter(h => h.visible).map(h => h.field || h.text),
            rows: rows,
            row_count: rows.length,
            pagination: pagination,
        }};
    }})()"""

    result = cdp.evaluate(js)
    if not result or result.get("error"):
        raise AgentError(result.get("error", "خطا در استخراج جدول"))

    log(f"📊 [کنسول] جدول یافت شد: {len(result.get('headers', []))} ستون، {result.get('row_count', 0)} ردیف | صفحه {result.get('pagination', {}).get('current_page', '?')} از {result.get('pagination', {}).get('total_pages', '?')}")

    ctx[store] = result
    return {"result": result, "message": f"جدول استخراج شد: {result.get('row_count', 0)} ردیف — صفحه {result.get('pagination', {}).get('current_page', '?')} از {result.get('pagination', {}).get('total_pages', '?')}"}


def _to_int(val, default=1):
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_float(val, default=1.0):
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _scrape_table_pages(cdp, step, ctx):
    """Scrape table data across multiple pages with auto-pagination."""
    max_pages = _to_int(step.get("max_pages"), 1)
    table_sel = step.get("table_selector") or ""
    next_sel = step.get("next_selector") or ""
    wait = _to_float(step.get("wait"), 2.0)
    include_hidden = bool(step.get("include_hidden", False))
    store = step.get("store_as") or "table_all_pages"

    all_rows = []
    headers = []
    pages_scraped = 0

    for page_num in range(1, max_pages + 1):
        log(f"📊 استخراج جدول — صفحه {page_num}/{max_pages}")

        # Scrape current page
        page_result = _scrape_table(cdp, {
            "table_selector": table_sel,
            "include_hidden": include_hidden,
            "store_as": "_page_data",
        }, ctx)

        page_data = ctx.get("_page_data", {})
        rows = page_data.get("rows", [])
        if not headers and page_data.get("headers"):
            headers = page_data["headers"]

        # Tag rows with page number
        for row in rows:
            row["_page"] = page_num
        all_rows.extend(rows)
        pages_scraped += 1

        if page_num >= max_pages:
            break

        # Find and click next page button
        pagination = page_data.get("pagination", {})
        actual_next = next_sel or pagination.get("next_selector", "")

        if not actual_next:
            log("⚠️ دکمه صفحه بعد یافت نشد — پایان پیمایش.")
            break

        # Check if next button exists and is clickable
        can_click = cdp.evaluate(f"""(() => {{
            const el = document.querySelector({_js_q(actual_next)});
            if (!el) return false;
            if (el.disabled || el.classList.contains('k-state-disabled') || el.getAttribute('disabled') !== null) return false;
            if (el.offsetParent === null) return false;
            return true;
        }})()""")

        if not can_click:
            log("⚠️ دکمه صفحه بعد غیرفعال — پایان پیمایش.")
            break

        # Click next
        _click(cdp, {"selector": actual_next, "wait": wait}, ctx)
        time.sleep(0.5)

        # Wait for table to refresh (content change)
        time.sleep(wait)

    # Save output file
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    fname = f"table_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = out_dir / fname
    output = {
        "headers": headers,
        "total_rows": len(all_rows),
        "pages_scraped": pages_scraped,
        "rows": all_rows,
        "scraped_at": dt.datetime.now().isoformat(),
    }
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx[store] = output
    return {
        "result": {"total_rows": len(all_rows), "pages_scraped": pages_scraped, "file": fname, "headers": headers},
        "message": f"جدول استخراج شد: {len(all_rows)} ردیف از {pages_scraped} صفحه → {fname}",
    }


def _bale_export(cdp, step, ctx):
    from bale_agent import collect_rows, collect_message, save_report, TEHRAN

    count = _to_int(step.get("count"), 10)
    timeout = _to_float(step.get("timeout"), 20.0)

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
    "while_loop":       _while_loop,
    "try_catch":        _try_catch,
    "detect_login":     _detect_login,
    "auto_login":       _auto_login,
    "scrape_table":     _scrape_table,
    "scrape_table_pages": _scrape_table_pages,
    "bale_export":      _bale_export,
}


def execute_step(cdp: CDP, step: dict, context: dict) -> dict:
    action = step.get("action")
    handler = ACTIONS.get(action)
    if not handler:
        raise AgentError(f"عملیات ناشناخته: {action}")
    try:
        result = handler(cdp, step, context)
        result["status"] = "success"
        return result
    except Exception as exc:
        log(f"❌ خطا در اجرا گام ({action}): {exc}")
        raise


def run_automation_steps(steps: list[dict], port: int = 9222) -> list[dict]:
    # ── Pre-flight: ensure browser is alive ──
    if not ensure_browser_ready(port):
        raise AgentError("مرورگر راه‌اندازی نشد. لطفاً به صورت دستی start-browser.cmd را اجرا کنید.")

    targets = endpoint_targets(port)
    target = None
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            target = t
            break
    if not target:
        raise AgentError("صفحه‌ای در مرورگر یافت نشد. مرورگر را باز کنید.")

    cdp = CDP(target["webSocketDebuggerUrl"], timeout=30)
    results = []
    context = {}
    try:
        for idx, step in enumerate(steps, 1):
            log(f"گام {idx}: {step.get('action')}")
            try:
                res = execute_step(cdp, step, context)
            except (ConnectionError, OSError, AgentError) as exc:
                # Connection lost mid-run — try reconnect once
                err_msg = str(exc)
                if "closed" in err_msg.lower() or "connection" in err_msg.lower() or "timeout" in err_msg.lower():
                    log("⚠️ ارتباط با مرورگر قطع شد. تلاش برای اتصال مجدد...")
                    try:
                        cdp.close()
                    except Exception:
                        pass
                    time.sleep(2)
                    if not ensure_browser_ready(port):
                        raise AgentError("اتصال مجدد به مرورگر ناموفق بود.")
                    targets = endpoint_targets(port)
                    target = next((t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
                    if not target:
                        raise AgentError("صفحه‌ای پس از اتصال مجدد یافت نشد.")
                    cdp = CDP(target["webSocketDebuggerUrl"], timeout=30)
                    res = execute_step(cdp, step, context)
                else:
                    raise
            results.append({"step": idx, "action": step.get("action"), **res})
    finally:
        cdp.close()
    return results


# ─── Built-in Templates ───

TEMPLATES = {
    "smart_login": {
        "name": "🔐 ورود هوشمند به سایت",
        "description": "تشخیص خودکار فرم ورود، پر کردن اطلاعات، مدیریت کپچا و تأیید ورود",
        "steps": [
            {"action": "auto_login", "url": "https://example.com/login", "username": "", "password": "", "human_on_captcha": True, "timeout": 30},
        ]
    },
    "login_basic": {
        "name": "ورود ساده به سایت",
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
            {"action": "type_human", "selector": "#password", "text": "", "char_delay": 0.06},
            {"action": "wait_for_human", "prompt": "لطفاً کپچا را حل کنید و دکمه ورود را بزنید.", "success_selector": ".dashboard", "timeout": 120},
        ]
    },
    "login_2fa": {
        "name": "🔑 ورود دو مرحله‌ای (OTP)",
        "description": "ورود هوشمند + انتظار برای وارد کردن کد تأیید پیامکی یا OTP توسط کاربر",
        "steps": [
            {"action": "auto_login", "url": "https://example.com/login", "username": "", "password": "", "human_on_captcha": True, "timeout": 30},
            {"action": "wait_for_human", "prompt": "کد تأیید پیامکی یا OTP را وارد کنید و دکمه تأیید را بزنید.", "success_selector": ".dashboard", "timeout": 180},
        ]
    },
    "detect_and_report": {
        "name": "🔍 شناسایی فرم ورود صفحه",
        "description": "بدون ورود — فقط فرم لاگین صفحه را شناسایی و گزارش می‌دهد",
        "steps": [
            {"action": "navigate", "url": "https://example.com/login", "wait": 3},
            {"action": "detect_login", "store_as": "login_info"},
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
    "scrape_cartable": {
        "name": "📊 استخراج و پیمایش جدول کارتابل",
        "description": "تشخیص هوشمند جدول، استخراج داده‌ها و پیمایش بین صفحات (Kendo Grid / کارتابل)",
        "steps": [
            {"action": "scrape_table_pages", "max_pages": 3, "wait": 2, "include_hidden": False, "store_as": "table_data"},
        ]
    },
    "bale_export": {
        "name": "استخراج پیام‌های اخیر بله",
        "description": "استخراج آخرین پیام از مخاطبان شخصی اخیر بله",
        "steps": [
            {"action": "bale_export", "count": 10, "timeout": 20},
        ]
    },
    "smart_conditional": {
        "name": "❓ فلوچارت هوشمند (شرط پیشرفته)",
        "description": "بررسی وضعیت صفحه و اجرای مسیرهای متفاوت بر اساس شرایط مختلف",
        "steps": [
            {"action": "auto_login", "url": "https://example.com/login", "username": "", "password": "", "human_on_captcha": True, "timeout": 30},
            {"action": "conditional", "conditions": [
                {"type": "url_contains", "value": "/dashboard"},
            ], "logic": "and", "then_steps": [
                {"action": "extract_text", "selector": "h1", "store_as": "page_title"},
            ], "else_steps": [
                {"action": "screenshot"},
                {"action": "wait_for_human", "prompt": "ورود ناموفق. لطفاً بررسی کنید.", "success_selector": ".dashboard", "timeout": 120},
            ]},
        ]
    },
    "while_pagination": {
        "name": "🔄 پیمایش شرطی (while)",
        "description": "تا زمانی که دکمه بعد وجود دارد صفحات را پیمایش و داده استخراج کن",
        "steps": [
            {"action": "navigate", "url": "https://example.com/list", "wait": 3},
            {"action": "while_loop", "conditions": [
                {"type": "selector_exists", "selector": ".next-page:not([disabled])"},
            ], "max_iterations": 50, "steps": [
                {"action": "extract_list", "selector": ".item", "store_as": "items"},
                {"action": "click", "selector": ".next-page", "wait": 2},
            ]},
        ]
    },
    "safe_automation": {
        "name": "🛡️ اتوماسیون امن (try/catch)",
        "description": "اجرای اتوماسیون با مدیریت خطا — در صورت بروز مشکل، اسکرین‌شات گرفته و ادامه می‌دهد",
        "steps": [
            {"action": "try_catch", "try_steps": [
                {"action": "auto_login", "url": "https://example.com/login", "username": "", "password": "", "timeout": 20},
                {"action": "scrape_table_pages", "max_pages": 3, "wait": 2},
            ], "catch_steps": [
                {"action": "screenshot"},
                {"action": "wait_for_human", "prompt": "خطا رخ داد. لطفاً وضعیت را بررسی کنید.", "success_selector": "body", "timeout": 300},
            ], "finally_steps": [
                {"action": "screenshot"},
            ]},
        ]
    },
}
