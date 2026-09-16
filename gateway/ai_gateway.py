"""Internet AI Gateway — synthesizes automation recipes from natural language.

Runs on an internet-connected host. Listens for user requests via the Bale
Tunnel (or HTTP), sends prompt to an LLM (Claude API, OpenAI, or local Ollama),
and parses out a valid `automation_engine` JSON step recipe to return over the tunnel.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

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


def synthesize(prompt: str, provider: str = "auto") -> dict[str, Any]:
    """Main entry: generate a recipe from natural language."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if provider == "auto":
        provider = "claude" if api_key else "ollama"

    if provider == "claude":
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        raw = _call_claude(prompt, api_key)
    elif provider == "ollama":
        raw = _call_ollama(prompt)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    steps = parse_recipe(raw)
    return {"prompt": prompt, "provider": provider, "steps": steps}


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
    print("ai_gateway self-check OK")
