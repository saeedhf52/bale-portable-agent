"""Internet AI Gateway — synthesizes automation recipes & answers queries from natural language.

Supports multiple LLM providers:
- Claude API (Anthropic)
- OpenAI API (GPT-4o, GPT-3.5, etc.)
- Ollama (Local open-source models)
- Custom OpenAI-compatible endpoints (vLLM, LMStudio, LocalAI, Enterprise LLMs)
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

import automation_db as db

SYSTEM_PROMPT = """You are an automation recipe generator for bale-portable-agent.
Your goal: take a user request and return ONLY a valid JSON array of step objects.

Supported step actions:
- navigate: {action: "navigate", url: "...", wait: 2}
- click: {action: "click", selector: "...", wait: 1}
- type / type_human: {action: "type", selector: "...", text: "..."}
- wait / wait_for_element / wait_element_gone / wait_for_human: {action: "wait", seconds: 2}
- extract_text / extract_list / crawl_links / screenshot: {action: "extract_text", selector: "...", store_as: "name"}
- scrape_table / scrape_table_pages: {action: "scrape_table", table_selector: "...", store_as: "name"}
- set_variable / evaluate_js: {action: "set_variable", key: "k", value: "v"}
- loop / while_loop / conditional / try_catch / auto_login / bale_export

Rules:
1. Output ONLY the JSON array inside a ```json ... ``` fence. No markdown chatter.
2. Ensure every step has required fields.
3. Keep recipes short, edge-case resilient (use try_catch or wait_for_element when appropriate).
"""


def _call_claude(prompt: str, api_key: str, model: str = "claude-3-5-sonnet-20241022") -> str:
    url = "https://api.anthropic.com/v1/messages"
    body = {
        "model": model,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["content"][0]["text"]


def _call_openai_compatible(prompt: str, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o") -> str:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(endpoint, data=json.dumps(body).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["choices"][0]["message"]["content"]


def _call_ollama(prompt: str, host: str = "http://localhost:11434", model: str = "llama3") -> str:
    url = f"{host.rstrip('/')}/api/generate"
    body = {"model": model, "system": SYSTEM_PROMPT, "prompt": prompt, "stream": False}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("response", "")


def parse_recipe(raw_text: str) -> list[dict]:
    """Extract JSON array of steps from LLM response text."""
    m = re.search(r"```(?:json)?\s*(\[\s*\{.*\}\s*\])\s*```", raw_text, re.DOTALL)
    blob = m.group(1) if m else raw_text.strip()
    steps = json.loads(blob)
    if not isinstance(steps, list):
        raise ValueError("LLM did not return a list")
    return steps


def synthesize(prompt: str, provider: str = "auto", model: str = "", api_key: str = "", base_url: str = "") -> dict[str, Any]:
    """Synthesize an automation recipe using configured LLM provider."""
    # Resolve settings from DB if not passed explicitly
    provider = provider if provider != "auto" else (os.environ.get("LLM_PROVIDER") or db.get_setting("llm_provider", "auto"))
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or db.get_setting("llm_api_key", "")
    model = model or os.environ.get("LLM_MODEL") or db.get_setting("llm_model", "")
    base_url = base_url or os.environ.get("LLM_BASE_URL") or db.get_setting("llm_base_url", "")

    if provider == "auto":
        if api_key and api_key.startswith("sk-ant"):
            provider = "claude"
        elif api_key:
            provider = "openai"
        else:
            provider = "ollama"

    if provider == "claude":
        if not api_key:
            raise ValueError("Claude API Key is missing. Configure `llm_api_key` in settings.")
        raw = _call_claude(prompt, api_key, model=model or "claude-3-5-sonnet-20241022")

    elif provider in {"openai", "custom"}:
        base = base_url or ("https://api.openai.com/v1" if provider == "openai" else "http://localhost:8000/v1")
        m_name = model or ("gpt-4o" if provider == "openai" else "custom-model")
        raw = _call_openai_compatible(prompt, api_key=api_key, base_url=base, model=m_name)

    elif provider == "ollama":
        host = base_url or "http://localhost:11434"
        m_name = model or "llama3"
        raw = _call_ollama(prompt, host=host, model=m_name)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    steps = parse_recipe(raw)
    return {"prompt": prompt, "provider": provider, "model": model, "steps": steps}


# ---- self-check ----
if __name__ == "__main__":
    mock_llm_out = """Here is your automation:
```json
[
  {"action": "navigate", "url": "https://example.com", "wait": 2},
  {"action": "extract_text", "selector": "h1", "store_as": "title"}
]
```
Done."""
    parsed = parse_recipe(mock_llm_out)
    assert len(parsed) == 2 and parsed[0]["action"] == "navigate"
    print("ai_gateway multi-model support OK")
