"""Dynamic skill loader for Bale Portable Agent.

A "skill" is either:
  1. JSON recipe: list of automation steps (same schema as automation_engine).
  2. Python module: exposes `run(context, args) -> dict` — free-form logic.

Skills live under `skills/` (bundled) or `skills_user/` (installed at runtime).
The manager discovers, validates, and executes them. No dynamic imports of
untrusted network content — skills must be dropped on disk explicitly.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
BUILTIN_DIR = ROOT / "skills"
USER_DIR = ROOT / "skills_user"


class SkillError(Exception):
    pass


def _iter_dirs():
    for d in (BUILTIN_DIR, USER_DIR):
        if d.is_dir():
            yield d


def list_skills() -> list[dict]:
    """Return all discoverable skills with metadata (kind, name, path, description)."""
    out = []
    for d in _iter_dirs():
        for path in sorted(d.iterdir()):
            if path.suffix == ".json":
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    out.append({
                        "name": path.stem, "kind": "recipe", "path": str(path),
                        "description": data.get("description", ""),
                        "steps": data.get("steps", []),
                    })
                except Exception as exc:
                    out.append({"name": path.stem, "kind": "recipe", "path": str(path),
                                "description": f"[invalid JSON: {exc}]", "steps": []})
            elif path.suffix == ".py" and not path.name.startswith("_"):
                out.append({
                    "name": path.stem, "kind": "python", "path": str(path),
                    "description": _module_docstring(path),
                })
    return out


def _module_docstring(path: Path) -> str:
    try:
        first = path.read_text(encoding="utf-8").split("\n", 30)
        for line in first:
            s = line.strip()
            if s.startswith(('"""', "'''")):
                return s.strip('"\' ')
    except Exception:
        pass
    return ""


def get_skill(name: str) -> dict:
    for s in list_skills():
        if s["name"] == name:
            return s
    raise SkillError(f"Skill not found: {name}")


def load_python_skill(path: str) -> Callable:
    """Load a python skill module and return its `run(context, args)` callable."""
    p = Path(path)
    spec = importlib.util.spec_from_file_location(f"skill_{p.stem}", p)
    if not spec or not spec.loader:
        raise SkillError(f"Cannot load skill: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise SkillError(f"Python skill missing `run(context, args)`: {path}")
    return mod.run


def install_skill(name: str, kind: str, content: str) -> str:
    """Persist a new skill under skills_user/. Returns the file path."""
    if kind not in {"recipe", "python"}:
        raise SkillError(f"Unsupported skill kind: {kind}")
    USER_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    if not safe:
        raise SkillError("Invalid skill name")
    ext = ".json" if kind == "recipe" else ".py"
    target = USER_DIR / f"{safe}{ext}"
    if kind == "recipe":
        json.loads(content)  # validate JSON before writing
    target.write_text(content, encoding="utf-8")
    return str(target)


def remove_skill(name: str) -> bool:
    for d in _iter_dirs():
        for ext in (".json", ".py"):
            p = d / f"{name}{ext}"
            if p.exists() and d == USER_DIR:
                p.unlink()
                return True
    return False


# ---- self-check ----
if __name__ == "__main__":
    USER_DIR.mkdir(parents=True, exist_ok=True)
    # Install and load a demo recipe.
    demo = json.dumps({"description": "demo", "steps": [{"action": "wait", "seconds": 0}]})
    p = install_skill("demo_recipe", "recipe", demo)
    assert Path(p).exists()
    s = get_skill("demo_recipe")
    assert s["kind"] == "recipe" and s["steps"]
    assert remove_skill("demo_recipe")
    print("skill_manager self-check OK")
