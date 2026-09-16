"""Live Browser Macro Recorder for Bale Portable Agent.

Captures browser interactions (clicks, inputs, element selections) via CDP
and converts them into executable automation step recipes.
"""
from __future__ import annotations

import json
import time
from typing import Any
from bale_agent import CDP, log, AgentError

RECORDER_JS_SNIPPET = """
(function() {
    if (window.__bale_macro_recorder_active) return 'already_active';
    window.__bale_macro_recorder_active = true;
    window.__bale_recorded_steps = [];

    function getSelector(el) {
        if (el.id) return '#' + el.id;
        if (el.getAttribute('data-testid')) return '[data-testid="' + el.getAttribute('data-testid') + '"]';
        if (el.getAttribute('aria-label')) return '[aria-label="' + el.getAttribute('aria-label') + '"]';
        let path = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.nodeName.toLowerCase();
            if (el.className && typeof el.className === 'string' && el.className.trim()) {
                let cls = el.className.trim().split(/\\s+/)[0];
                if (cls) selector += '.' + cls;
            }
            path.unshift(selector);
            el = el.parentNode;
            if (path.length >= 3) break;
        }
        return path.join(' > ');
    }

    document.addEventListener('click', function(e) {
        if (!window.__bale_macro_recorder_active) return;
        let selector = getSelector(e.target);
        window.__bale_recorded_steps.push({
            action: 'click',
            selector: selector,
            wait: 1,
            text_preview: (e.target.innerText || '').slice(0, 30)
        });
    }, true);

    document.addEventListener('change', function(e) {
        if (!window.__bale_macro_recorder_active) return;
        let tag = e.target.tagName.toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') {
            let selector = getSelector(e.target);
            window.__bale_recorded_steps.push({
                action: 'type',
                selector: selector,
                text: e.target.value,
                store_as: e.target.name || null
            });
        }
    }, true);

    return 'started';
})()
"""

STOP_SNIPPET = """
(function() {
    window.__bale_macro_recorder_active = false;
    let steps = window.__bale_recorded_steps || [];
    window.__bale_recorded_steps = [];
    return JSON.stringify(steps);
})()
"""


class MacroRecorder:
    def __init__(self, cdp: CDP):
        self.cdp = cdp
        self.recording = False

    def start(self) -> str:
        res = self.cdp.evaluate(RECORDER_JS_SNIPPET)
        self.recording = True
        log("🔴 رکورد اتوماسیون (ماکرو) در مرورگر فعال شد. در حال ضبط عملیات کاربر...")
        return res

    def stop(self) -> list[dict]:
        if not self.recording:
            return []
        raw = self.cdp.evaluate(STOP_SNIPPET)
        self.recording = False
        steps = json.loads(raw) if isinstance(raw, str) else (raw or [])
        log(f"⏹ رکورد متوقف شد. {len(steps)} گام اتوماسیون استخراج گردید.")
        return steps

    def record_selection(self, var_name: str) -> dict:
        """Capture the currently selected element/text on screen into a variable."""
        expr = """
        (function() {
            let sel = window.getSelection();
            let text = sel ? sel.toString().trim() : '';
            let anchor = sel && sel.anchorNode ? (sel.anchorNode.parentElement || sel.anchorNode) : null;
            let selector = anchor ? (anchor.id ? '#' + anchor.id : anchor.tagName.toLowerCase()) : 'body';
            return JSON.stringify({text: text, selector: selector});
        })()
        """
        raw = self.cdp.evaluate(expr)
        data = json.loads(raw)
        return {
            "action": "extract_text",
            "selector": data["selector"],
            "store_as": var_name,
            "sample_value": data["text"],
        }


# ---- self-check ----
if __name__ == "__main__":
    print("macro_recorder module loaded OK")
