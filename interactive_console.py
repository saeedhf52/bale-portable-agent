"""Interactive Console REPL for Bale Portable AI Agent (Claude Code / OpenCode Style).

Rich CLI shell with auto-completion, interactive menus, macro recorder control,
LLM configuration, and admin authentication.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import automation_db as db
import admin_auth
from agent_core import AgentCore
from bale_agent import probe_endpoint, endpoint_targets, select_target, CDP, ensure_browser_ready
from macro_recorder import MacroRecorder

try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline  # Windows fallback
    except ImportError:
        readline = None

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}┌─────────────────────────────────────────────────────────────┐
│  🤖 Bale Portable AI Agent — Interactive Shell (v2.0)        │
│  Enterprise Air-Gapped Automation, CDP & RAG Memory Platform│
└─────────────────────────────────────────────────────────────┘{RESET}
"""
    print(banner)


class InteractiveConsole:
    def __init__(self):
        db.init_db()
        self.agent = AgentCore()
        self.logged_in = admin_auth.verify_session("default")
        self.recorder: MacroRecorder | None = None
        self._setup_autocomplete()

    def _setup_autocomplete(self):
        if not readline:
            return
        commands = [
            "help", "status", "list", "run", "record", "stop-record",
            "ask", "set-llm", "set-bot", "set-admin", "login", "exit"
        ]

        def completer(text, state):
            options = [c for c in commands if c.startswith(text)]
            if state < len(options):
                return options[state]
            return None

        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")

    def print_status(self):
        cdp_active = probe_endpoint(9222)
        bot_token = db.get_setting("bot_token")
        llm_provider = db.get_setting("llm_provider", "auto")
        llm_model = db.get_setting("llm_model", "default")

        print(f"\n{BOLD}📊 System Status:{RESET}")
        print(f"  • Chrome CDP (9222):  {GREEN}✅ Connected{RESET}" if cdp_active else f"  • Chrome CDP (9222):  {RED}❌ Disconnected{RESET}")
        print(f"  • Web GUI (8080):     {GREEN}✅ http://127.0.0.1:8080{RESET}")
        print(f"  • Bale Bot Token:     {GREEN}✅ Configured{RESET}" if bot_token else f"  • Bale Bot Token:     {YELLOW}⚠️ Not set{RESET}")
        print(f"  • AI LLM Provider:    {CYAN}{llm_provider} ({llm_model}){RESET}")
        print(f"  • Admin Protection:   {GREEN}✅ Active{RESET}" if admin_auth.is_admin_configured() else f"  • Admin Protection:   {YELLOW}⚠️ Open (no password set){RESET}\n")

    def run(self):
        print_banner()
        self.print_status()

        while True:
            try:
                prompt_str = f"{CYAN}{BOLD}agent{RESET}> "
                line = input(prompt_str).strip()
                if not line:
                    continue

                if line in {"exit", "quit"}:
                    print(f"{GREEN}👋 Goodbye!{RESET}")
                    break

                if line == "help":
                    print(f"\n{BOLD}Available Commands:{RESET}")
                    print("  status                   Show system connections and status")
                    print("  list                     List all installed skills & automations")
                    print("  run <skill_name>         Execute an automation skill")
                    print("  record                   Start browser interaction recorder (macro)")
                    print("  stop-record [name]       Stop macro recorder & save recorded steps")
                    print("  ask <prompt>             Query local RAG knowledge base")
                    print("  set-llm <provider>       Configure AI model (claude/openai/ollama/custom)")
                    print("  set-bot <token>          Configure Bale Bot API token")
                    print("  set-admin                Set admin password for console & Web GUI")
                    print("  login                    Login with admin password\n")
                    continue

                parts = line.split(maxsplit=1)
                cmd = parts[0]
                rest = parts[1] if len(parts) > 1 else ""

                if cmd == "status":
                    self.print_status()

                elif cmd == "login":
                    pw = input("Admin Password: ")
                    if admin_auth.verify_admin_password(pw):
                        self.logged_in = True
                        print(f"{GREEN}✅ Admin authentication successful.{RESET}")
                    else:
                        print(f"{RED}❌ Invalid password.{RESET}")

                elif cmd == "set-admin":
                    new_pw = input("Enter new admin password: ")
                    if new_pw:
                        admin_auth.set_admin_password(new_pw)
                        self.logged_in = True
                        print(f"{GREEN}✅ Admin password updated.{RESET}")

                elif cmd == "list":
                    skills = self.agent.list_skills()
                    print(f"\n{BOLD}📦 Installed Skills:{RESET}")
                    for s in skills:
                        print(f"  • {CYAN}{s['name']}{RESET} ({s['kind']}): {s.get('description', '')}")
                    print()

                elif cmd == "run":
                    if not rest:
                        print(f"{YELLOW}Usage: run <skill_name> [json_args]{RESET}")
                        continue
                    r_parts = rest.split(maxsplit=1)
                    name = r_parts[0]
                    args = json.loads(r_parts[1]) if len(r_parts) > 1 else {}
                    print(f"🚀 Running skill '{name}'...")
                    res = self.agent.run_skill(name, args)
                    print(json.dumps(res, ensure_ascii=False, indent=2))

                elif cmd == "record":
                    try:
                        print("🔄 در حال بررسی و آماده‌سازی مرورگر...")
                        if not ensure_browser_ready(9222):
                            print(f"{RED}❌ مرورگر راه‌اندازی نشد.{RESET}")
                            continue
                        targets = endpoint_targets(9222)
                        target = select_target(targets)
                        cdp = CDP(target["webSocketDebuggerUrl"])
                        self.recorder = MacroRecorder(cdp)
                        self.recorder.start()
                        print(f"{RED}{BOLD}🔴 Recording browser macro! Perform clicks/inputs in Chrome. Type 'stop-record' when done.{RESET}")
                    except Exception as exc:
                        print(f"{RED}❌ Failed to start recorder: {exc}{RESET}")

                elif cmd == "stop-record":
                    if not self.recorder:
                        print(f"{YELLOW}No recorder active.{RESET}")
                        continue
                    steps = self.recorder.stop()
                    name = rest or f"recorded_{int(time.time())}"
                    if steps:
                        saved_id = db.save_automation(name, "Recorded browser macro", json.dumps(steps, ensure_ascii=False))
                        print(f"{GREEN}✅ Macro recorded and saved as automation #{saved_id} ('{name}'){RESET}")
                        print(json.dumps(steps, ensure_ascii=False, indent=2))
                    self.recorder = None

                elif cmd == "ask":
                    if not rest:
                        print(f"{YELLOW}Usage: ask <query>{RESET}")
                        continue
                    res = db.search_knowledge(rest)
                    print(json.dumps(res, ensure_ascii=False, indent=2))

                elif cmd == "set-llm":
                    if not rest:
                        print(f"{YELLOW}Usage: set-llm <provider> (claude/openai/ollama/custom){RESET}")
                        continue
                    prov_parts = rest.split()
                    provider = prov_parts[0]
                    db.set_setting("llm_provider", provider)
                    if len(prov_parts) > 1:
                        db.set_setting("llm_api_key", prov_parts[1])
                    print(f"{GREEN}✅ LLM Provider set to '{provider}'{RESET}")

                elif cmd == "set-bot":
                    if not rest:
                        print(f"{YELLOW}Usage: set-bot <token>{RESET}")
                        continue
                    db.set_setting("bot_token", rest)
                    print(f"{GREEN}✅ Bale Bot Token saved.{RESET}")

                else:
                    print(f"{YELLOW}Unknown command '{cmd}'. Type 'help' for available commands.{RESET}")

            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break
            except Exception as exc:
                print(f"{RED}❌ Error: {exc}{RESET}")


def main():
    console = InteractiveConsole()
    console.run()


if __name__ == "__main__":
    main()
