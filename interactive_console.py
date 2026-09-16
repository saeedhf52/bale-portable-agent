"""Interactive Console REPL for Bale Portable AI Agent (Claude Code / OpenCode Style).

Rich CLI shell with auto-completion, slash commands (/mode, /config, /llm, /record, /ask),
interactive mode switcher, macro recorder control, LLM configuration, and admin auth.
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
from gateway import ai_gateway

try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline  # Windows fallback
    except ImportError:
        readline = None

# ANSI colors & formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

MODES = {
    "auto": "🤖 Auto Mode — AI interprets natural language into automations automatically",
    "agent": "⚡ Agent Mode — Standard execution of installed skills & commands",
    "plan": "📋 Plan Mode — Preview generated automation steps before executing",
    "strict": "🔒 Strict Mode — Require admin confirmation before browser actions",
}


def safe_print(text):
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or "utf-8"
            print(str(text).encode(encoding, errors="replace").decode(encoding, errors="replace"), flush=True)
        except Exception:
            pass


def print_banner():
    banner = f"""
{CYAN}{BOLD}+-------------------------------------------------------------+
|  Bale Portable AI Agent -- Interactive Shell (v2.5)          |
|  Enterprise Air-Gapped Automation, CDP & RAG Memory Platform|
+-------------------------------------------------------------+{RESET}
"""
    safe_print(banner)


class InteractiveConsole:
    def __init__(self):
        db.init_db()
        self.agent = AgentCore()
        self.logged_in = admin_auth.verify_session("default")
        self.recorder: MacroRecorder | None = None
        self.mode = db.get_setting("agent_mode", "auto")
        self._setup_autocomplete()

    def _setup_autocomplete(self):
        if not readline:
            return
        commands = [
            "/help", "/mode", "/config", "/llm", "/record", "/stop",
            "/ask", "/skills", "/status", "/clear", "/exit",
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
        llm_base_url = db.get_setting("llm_base_url", "default")
        llm_key = db.get_setting("llm_api_key", "")
        has_key = "Set" if llm_key else "Not set"

        safe_print(f"\n{BOLD}System Status:{RESET}")
        safe_print(f"  * Active Mode:        {CYAN}{BOLD}{self.mode.upper()}{RESET} ({MODES.get(self.mode, '')})")
        safe_print(f"  * Chrome CDP (9222):  {GREEN}[OK] Connected{RESET}" if cdp_active else f"  * Chrome CDP (9222):  {RED}[-] Disconnected{RESET}")
        safe_print(f"  * Web GUI (8080):     {GREEN}[OK] http://127.0.0.1:8080{RESET}")
        safe_print(f"  * Bale Bot Token:     {GREEN}[OK] Configured{RESET}" if bot_token else f"  * Bale Bot Token:     {YELLOW}[!] Not set{RESET}")
        safe_print(f"  * AI Provider:        {CYAN}{llm_provider}{RESET} (Model: {llm_model}, Key: {has_key})")
        if llm_base_url and llm_base_url != "default":
            safe_print(f"  * LLM Base Endpoint:  {DIM}{llm_base_url}{RESET}")
        safe_print(f"  * Admin Protection:   {GREEN}[OK] Active{RESET}" if admin_auth.is_admin_configured() else f"  * Admin Protection:   {YELLOW}[!] Open (no password set){RESET}\n")

    def handle_mode(self, new_mode: str):
        if not new_mode:
            safe_print(f"\n{BOLD}Current Mode:{RESET} {CYAN}{self.mode}{RESET}")
            safe_print(f"{BOLD}Available Modes:{RESET}")
            for m, desc in MODES.items():
                mark = "> " if m == self.mode else "  "
                safe_print(f"  {mark}{CYAN}{m:8s}{RESET} : {desc}")
            safe_print(f"\nUse {BOLD}/mode <name>{RESET} to switch.\n")
            return
        new_mode = new_mode.lower().strip()
        if new_mode in MODES:
            self.mode = new_mode
            db.set_setting("agent_mode", new_mode)
            safe_print(f"{GREEN}[OK] Mode switched to '{new_mode}': {MODES[new_mode]}{RESET}")
        else:
            safe_print(f"{RED}[-] Invalid mode. Choose from: {', '.join(MODES.keys())}{RESET}")

    def handle_llm_config(self, args_str: str):
        if not args_str:
            safe_print(f"\n{BOLD}LLM Configuration Settings:{RESET}")
            safe_print(f"  1. Provider:  {db.get_setting('llm_provider', 'auto')} (claude / openai / ollama / custom)")
            safe_print(f"  2. Model:     {db.get_setting('llm_model', 'default')}")
            safe_print(f"  3. Base URL:  {db.get_setting('llm_base_url', 'default')}")
            safe_print(f"  4. API Key:   {'******' if db.get_setting('llm_api_key') else 'Not set'}")
            safe_print(f"\n{DIM}Usage: /llm provider=claude key=sk-ant-... model=claude-3-5-sonnet{RESET}\n")
            return

        pairs = args_str.split()
        for p in pairs:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.lower().strip()
                if k == "provider":
                    db.set_setting("llm_provider", v)
                elif k == "key":
                    db.set_setting("llm_api_key", v)
                elif k == "model":
                    db.set_setting("llm_model", v)
                elif k in {"url", "base_url"}:
                    db.set_setting("llm_base_url", v)
        safe_print(f"{GREEN}[OK] LLM configuration updated successfully.{RESET}")

    def run(self):
        print_banner()
        self.print_status()

        while True:
            try:
                prompt_str = f"{CYAN}{BOLD}[{self.mode}] agent{RESET}> "
                line = input(prompt_str).strip()
                if not line:
                    continue

                # Slash command aliases
                if line in {"/exit", "/quit", "exit", "quit"}:
                    print(f"{GREEN}👋 Goodbye!{RESET}")
                    break

                if line == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    print_banner()
                    continue

                if line in {"/help", "help"}:
                    print(f"\n{BOLD}Available Commands & Slash Commands:{RESET}")
                    print("  /mode [auto|agent|plan|strict]  Switch agent execution mode")
                    print("  /llm [k=v ...]                  Configure AI models (provider/key/model/url)")
                    print("  /record                         Start macro recorder with persistent web toolbar")
                    print("  /stop [title]                   Stop recorder & save automation to database")
                    print("  /ask <query>                    Search local RAG memory base")
                    print("  /skills                         List all installed automation skills")
                    print("  /status                         Show system connections and status")
                    print("  /clear                          Clear terminal screen")
                    print("  set-bot <token>                 Configure Bale Bot API token")
                    print("  set-admin                       Set admin password")
                    print("  login                           Login with admin password\n")
                    continue

                if line.startswith("/mode"):
                    parts = line.split(maxsplit=1)
                    self.handle_mode(parts[1] if len(parts) > 1 else "")
                    continue

                if line.startswith("/llm"):
                    parts = line.split(maxsplit=1)
                    self.handle_llm_config(parts[1] if len(parts) > 1 else "")
                    continue

                if line in {"/status", "status"}:
                    self.print_status()
                    continue

                if line in {"/skills", "/list", "list"}:
                    skills = self.agent.list_skills()
                    print(f"\n{BOLD}📦 Installed Skills:{RESET}")
                    for s in skills:
                        print(f"  • {CYAN}{s['name']}{RESET} ({s['kind']}): {s.get('description', '')}")
                    print()
                    continue

                if line.startswith("/record") or line == "record":
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
                        print(f"{RED}{BOLD}🔴 Recording browser macro! Complete steps in Chrome. Type '/stop [title]' when done.{RESET}")
                    except Exception as exc:
                        print(f"{RED}❌ Failed to start recorder: {exc}{RESET}")
                    continue

                if line.startswith("/stop") or line.startswith("stop-record"):
                    if not self.recorder:
                        print(f"{YELLOW}No recorder active.{RESET}")
                        continue
                    parts = line.split(maxsplit=1)
                    def_title = parts[1] if len(parts) > 1 else ""
                    res = self.recorder.stop(default_name=def_title)
                    if res.get("id"):
                        print(f"{GREEN}✅ Automation #{res['id']} ('{res['title']}') saved with {len(res['steps'])} steps!{RESET}")
                    self.recorder = None
                    continue

                if line.startswith("/ask") or line.startswith("ask"):
                    parts = line.split(maxsplit=1)
                    query = parts[1] if len(parts) > 1 else ""
                    if not query:
                        print(f"{YELLOW}Usage: /ask <query>{RESET}")
                        continue
                    res = db.search_knowledge(query)
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                    continue

                # Admin commands
                if line == "login":
                    pw = input("Admin Password: ")
                    if admin_auth.verify_admin_password(pw):
                        self.logged_in = True
                        print(f"{GREEN}✅ Admin authentication successful.{RESET}")
                    else:
                        print(f"{RED}❌ Invalid password.{RESET}")
                    continue

                if line == "set-admin":
                    new_pw = input("Enter new admin password: ")
                    if new_pw:
                        admin_auth.set_admin_password(new_pw)
                        self.logged_in = True
                        print(f"{GREEN}✅ Admin password updated.{RESET}")
                    continue

                if line.startswith("set-bot"):
                    parts = line.split(maxsplit=1)
                    if len(parts) > 1:
                        db.set_setting("bot_token", parts[1])
                        print(f"{GREEN}✅ Bale Bot Token saved.{RESET}")
                    continue

                # Execution: skill or AI natural language
                if line.startswith("run "):
                    rest = line[4:]
                    r_parts = rest.split(maxsplit=1)
                    name = r_parts[0]
                    args = json.loads(r_parts[1]) if len(r_parts) > 1 else {}
                    print(f"🚀 Running skill '{name}'...")
                    res = self.agent.run_skill(name, args)
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                    continue

                # If natural language and mode == 'auto' or 'plan'
                print(f"🧠 Synthesizing AI automation for: '{line}'...")
                try:
                    synth = ai_gateway.synthesize(line)
                    steps = synth.get("steps", [])
                    print(f"📋 Generated {len(steps)} automation steps.")
                    if self.mode == "plan":
                        print(json.dumps(steps, ensure_ascii=False, indent=2))
                        confirm = input("Execute steps? [y/N]: ").strip().lower()
                        if confirm != "y":
                            print("Cancelled.")
                            continue

                    print("🚀 Executing synthesized automation...")
                    cmd_payload = {"cmd": "run", "steps": steps}
                    res = self.agent.handle_command(cmd_payload)
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                except Exception as exc:
                    print(f"{RED}❌ AI synthesis/execution failed: {exc}{RESET}")

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
