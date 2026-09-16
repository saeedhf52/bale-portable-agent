"""Live Browser Macro Recorder for Bale Portable Agent with Floating Web UI Toolbar.

Injects an interactive floating control panel directly into the web page.
Allows step recording, visual element picking, variable extraction, conditional branching,
and immediate saving.
"""
from __future__ import annotations

import json
import time
from typing import Any
from bale_agent import CDP, log, AgentError

FLOATING_TOOLBAR_JS = """
(function() {
    if (document.getElementById('bale-recorder-toolbar')) {
        return 'already_running';
    }

    window.__bale_macro_recorder_active = true;
    window.__bale_recorded_steps = [];
    window.__bale_picking_var = false;

    function getSelector(el) {
        if (!el || el === document.body) return 'body';
        if (el.id) return '#' + el.id;
        if (el.getAttribute('data-testid')) return '[data-testid="' + el.getAttribute('data-testid') + '"]';
        if (el.getAttribute('aria-label')) return '[aria-label="' + el.getAttribute('aria-label') + '"]';
        let path = [];
        while (el && el.nodeType === Node.ELEMENT_NODE && el !== document.body) {
            let selector = el.nodeName.toLowerCase();
            if (el.className && typeof el.className === 'string' && el.className.trim()) {
                let cls = el.className.trim().split(/\\s+/)[0];
                if (cls && !cls.startsWith('bale-rec')) selector += '.' + cls;
            }
            path.unshift(selector);
            el = el.parentNode;
            if (path.length >= 3) break;
        }
        return path.join(' > ');
    }

    // ── Create Floating UI Toolbar ──
    const toolbar = document.createElement('div');
    toolbar.id = 'bale-recorder-toolbar';
    toolbar.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 99999999;
        background: #1e1e2e;
        color: #cdd6f4;
        padding: 12px 16px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 13px;
        direction: rtl;
        display: flex;
        align-items: center;
        gap: 10px;
        border: 1px solid #45475a;
        user-select: none;
    `;

    toolbar.innerHTML = `
        <div style="display:flex; align-items:center; gap:6px;">
            <span style="width:10px; height:10px; background:#f38ba8; border-radius:50%; display:inline-block; animation:pulse 1s infinite;"></span>
            <span style="font-weight:bold; color:#f38ba8;">ضبط ماکرو (<span id="bale-step-count">0</span>)</span>
        </div>
        <button id="bale-btn-pick" style="background:#313244; color:#89b4fa; border:1px solid #45475a; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px;">📌 ذخیره در متغیر</button>
        <button id="bale-btn-cond" style="background:#313244; color:#f9e2af; border:1px solid #45475a; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px;">⚡ شرط</button>
        <button id="bale-btn-stop" style="background:#a6e3a1; color:#11111b; border:none; padding:6px 14px; border-radius:6px; cursor:pointer; font-weight:bold; font-size:12px;">⏹ ذخیره و پایان</button>
    `;

    document.body.appendChild(toolbar);

    function updateCount() {
        let el = document.getElementById('bale-step-count');
        if (el) el.innerText = window.__bale_recorded_steps.length;
    }

    // ── Click Recorder ──
    document.addEventListener('click', function(e) {
        if (!window.__bale_macro_recorder_active) return;
        if (toolbar.contains(e.target)) return;

        let selector = getSelector(e.target);

        if (window.__bale_picking_var) {
            e.preventDefault();
            e.stopPropagation();
            window.__bale_picking_var = false;
            document.body.style.cursor = 'default';

            let varName = prompt('نام متغیر برای ذخیره این المان را وارد کنید (مثلا: chat_title, price, token):');
            if (varName) {
                window.__bale_recorded_steps.push({
                    action: 'extract_text',
                    selector: selector,
                    store_as: varName.trim(),
                    sample_value: (e.target.innerText || '').slice(0, 50)
                });
                updateCount();
                alert('✅ ذخیره در متغیر ' + varName + ' با موفقیت ثبت شد.');
            }
            return;
        }

        window.__bale_recorded_steps.push({
            action: 'click',
            selector: selector,
            wait: 1,
            text_preview: (e.target.innerText || '').slice(0, 30)
        });
        updateCount();
    }, true);

    // ── Input Recorder ──
    document.addEventListener('change', function(e) {
        if (!window.__bale_macro_recorder_active || toolbar.contains(e.target)) return;
        let tag = e.target.tagName.toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') {
            let selector = getSelector(e.target);
            window.__bale_recorded_steps.push({
                action: 'type',
                selector: selector,
                text: e.target.value,
                store_as: e.target.name || null
            });
            updateCount();
        }
    }, true);

    // ── Toolbar Button Events ──
    document.getElementById('bale-btn-pick').addEventListener('click', function() {
        window.__bale_picking_var = true;
        document.body.style.cursor = 'crosshair';
        alert('👉 روی هر المانی در صفحه کلیک کنید تا متنی که دارد در متغیر ذخیره شود.');
    });

    document.getElementById('bale-btn-cond').addEventListener('click', function() {
        let varName = prompt('نام متغیر مورد نظر برای بررسی شرط:');
        if (!varName) return;
        let expected = prompt('مقدار مورد انتظار (مثلا: "success" یا "ورود"):');
        window.__bale_recorded_steps.push({
            action: 'conditional',
            variable: varName,
            operator: 'equals',
            expected: expected,
            if_true: [],
            if_false: []
        });
        updateCount();
        alert('⚡ شرط روی متغیر ' + varName + ' اضافه شد.');
    });

    document.getElementById('bale-btn-stop').addEventListener('click', function() {
        window.__bale_macro_recorder_finished = true;
        toolbar.remove();
    });

    return 'started_with_ui';
})()
"""

STOP_SNIPPET = """
(function() {
    window.__bale_macro_recorder_active = false;
    let tb = document.getElementById('bale-recorder-toolbar');
    if (tb) tb.remove();
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
        res = self.cdp.evaluate(FLOATING_TOOLBAR_JS)
        self.recording = True
        log("🔴 منوی شناور ماکرو رکوردر در مرورگر فعال شد. کنترل‌ها از داخل مرورگر یا کنسول امکان‌پذیر است.")
        return res

    def stop(self) -> list[dict]:
        if not self.recording:
            return []
        raw = self.cdp.evaluate(STOP_SNIPPET)
        self.recording = False
        steps = json.loads(raw) if isinstance(raw, str) else (raw or [])
        log(f"⏹ رکورد متوقف شد. {len(steps)} گام اتوماسیون هوشمند استخراج گردید.")
        return steps


# ---- self-check ----
if __name__ == "__main__":
    print("macro_recorder UI module loaded OK")
