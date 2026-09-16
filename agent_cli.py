"""CLI Runner for Bale Portable AI Agent.

Usage:
  python agent_cli.py start         # Start master launcher (GUI + Bot + REPL)
  python agent_cli.py list-skills
  python agent_cli.py run-skill <name> [--args '{"key":"val"}']
  python agent_cli.py install-skill <name> <kind> <path_or_json>
  python agent_cli.py mcp           # Run MCP stdio server
  python agent_cli.py ask <prompt>  # Search RAG knowledge
  python agent_cli.py set-bot-token <token>
  python agent_cli.py set-llm <provider> [--key API_KEY] [--model MODEL] [--url BASE_URL]
  python agent_cli.py tunnel-encode <json_file_or_string>
  python agent_cli.py tunnel-decode <frame1> [<frame2> ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_core import AgentCore
import bale_tunnel
import automation_db as db


def main():
    parser = argparse.ArgumentParser(description="Bale Portable AI Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # start
    sub.add_parser("start", help="Start full master launcher (GUI, Bot, Interactive REPL)")

    # list-skills
    sub.add_parser("list-skills", help="List all available skills")

    # run-skill
    p_run = sub.add_parser("run-skill", help="Run a skill by name")
    p_run.add_argument("name", help="Skill name")
    p_run.add_argument("--args", default="{}", help="JSON string of arguments")

    # install-skill
    p_inst = sub.add_parser("install-skill", help="Install a new skill")
    p_inst.add_argument("name", help="Skill name")
    p_inst.add_argument("kind", choices=["recipe", "python"], help="Skill kind")
    p_inst.add_argument("content", help="JSON recipe string or python code string (or file path)")

    # mcp
    sub.add_parser("mcp", help="Run MCP stdio server for Claude Desktop / Cursor")

    # ask / RAG
    p_ask = sub.add_parser("ask", help="Query local RAG knowledge base")
    p_ask.add_argument("query", help="Search query")

    # set-bot-token
    p_tok = sub.add_parser("set-bot-token", help="Set Bale Bot API Token")
    p_tok.add_argument("token", help="Bale Bot Token string")

    # set-llm
    p_llm = sub.add_parser("set-llm", help="Configure AI Model provider & credentials")
    p_llm.add_argument("provider", choices=["claude", "openai", "ollama", "custom", "auto"], help="LLM Provider")
    p_llm.add_argument("--key", default="", help="API Key")
    p_llm.add_argument("--model", default="", help="Model name")
    p_llm.add_argument("--url", default="", help="Base URL for custom/ollama endpoint")

    # tunnel-encode
    p_enc = sub.add_parser("tunnel-encode", help="Encode payload into Bale text frames")
    p_enc.add_argument("data", help="JSON string or path to JSON file")
    p_enc.add_argument("--key", default="", help="Optional encryption key")

    # tunnel-decode
    p_dec = sub.add_parser("tunnel-decode", help="Decode Bale text frames")
    p_dec.add_argument("frames", nargs="+", help="Text frames")
    p_dec.add_argument("--key", default="", help="Optional encryption key")

    args = parser.parse_args()
    db.init_db()
    agent = AgentCore()

    if args.command == "start":
        import agent_launcher
        agent_launcher.main()

    elif args.command == "list-skills":
        skills = agent.list_skills()
        print(json.dumps(skills, ensure_ascii=False, indent=2))

    elif args.command == "run-skill":
        parsed_args = json.loads(args.args)
        res = agent.run_skill(args.name, parsed_args)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "install-skill":
        content = args.content
        if Path(content).is_file():
            content = Path(content).read_text(encoding="utf-8")
        res = agent.install_skill(args.name, args.kind, content)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "mcp":
        from mcp_adapter import MCPServer
        MCPServer(agent).serve()

    elif args.command == "ask":
        res = db.search_knowledge(args.query)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "set-bot-token":
        db.set_setting("bot_token", args.token)
        print(f"✅ Bale Bot Token saved.")

    elif args.command == "set-llm":
        db.set_setting("llm_provider", args.provider)
        if args.key:
            db.set_setting("llm_api_key", args.key)
        if args.model:
            db.set_setting("llm_model", args.model)
        if args.url:
            db.set_setting("llm_base_url", args.url)
        print(f"✅ LLM provider configured: {args.provider}")

    elif args.command == "tunnel-encode":
        data = args.data
        if Path(data).is_file():
            data = Path(data).read_text(encoding="utf-8")
        obj = json.loads(data) if isinstance(data, str) and data.startswith(("{", "[")) else data
        frames = bale_tunnel.encode(obj, key=args.key.encode() if args.key else b"")
        for f in frames:
            print(f)

    elif args.command == "tunnel-decode":
        res = bale_tunnel.decode(args.frames, key=args.key.encode() if args.key else b"")
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
