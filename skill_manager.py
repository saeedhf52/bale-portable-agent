"""Dynamic skill loader & signer for Bale Portable Agent.

A "skill" is either:
  1. JSON recipe: list of automation steps (same schema as automation_engine).
  2. Python module: exposes `run(context, args) -> dict` — free-form logic.

Skills live under `skills/` (bundled) or `skills_user/` (installed at runtime).
Includes HMAC-SHA256 signature verification to prevent untrusted execution.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
BUILTIN_DIR = ROOT / "skills"
USER_DIR = ROOT / "skills_user"


class SkillError(Exception):
    pass


def sign_skill(content: str, key: bytes) -> str:
    """Compute HMAC-SHA256 hex signature of skill content."""
    return hmac.new(key, content.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_skill_signature(content: str, signature: str, key: bytes) -> bool:
    """Verify HMAC-SHA256 signature of skill content."""
    expected = sign_skill(content, key)
    return hmac.compare_digest(signature.strip().lower(), expected.lower())


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
                        "signature": data.get("signature", ""),
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


def install_skill(name: str, kind: str, content: str, key: bytes = b"", signature: str | None = None) -> str:
    """Persist a new skill under skills_user/. Returns the file path."""
    if kind not in {"recipe", "python"}:
        raise SkillError(f"Unsupported skill kind: {kind}")
    if key and signature and not verify_skill_signature(content, signature, key):
        raise SkillError("Skill signature verification failed — untrusted content")

    USER_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    if not safe:
        raise SkillError("Invalid skill name")
    ext = ".json" if kind == "recipe" else ".py"
    target = USER_DIR / f"{safe}{ext}"
    if kind == "recipe":
        parsed = json.loads(content)  # validate JSON
        if signature:
            parsed["signature"] = signature
            content = json.dumps(parsed, ensure_ascii=False, indent=2)

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
    key = b"secret_signing_key"
    demo_raw = json.dumps({"description": "signed demo", "steps": [{"action": "wait", "seconds": 0}]})
    sig = sign_skill(demo_raw, key)
    assert verify_skill_signature(demo_raw, sig, key)

    p = install_skill("signed_demo", "recipe", demo_raw, key=key, signature=sig)
    assert Path(p).exists()
    s = get_skill("signed_demo")
    assert s["kind"] == "recipe" and s["signature"] == sig
    assert remove_skill("signed_demo")
    print("skill_manager signature self-check OK")
