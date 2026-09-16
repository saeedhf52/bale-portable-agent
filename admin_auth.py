"""Admin Authentication & Security Manager for Bale Portable AI Agent.

Handles password hashing, token validation, and administrative access control.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import automation_db as db

SESSION_TOKENS: dict[str, float] = {}  # token -> expire_timestamp
TOKEN_TTL = 86400  # 24 hours


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000).hex()


def is_admin_configured() -> bool:
    return bool(db.get_setting("admin_password_hash"))


def set_admin_password(password: str):
    salt = os.urandom(16)
    pw_hash = _hash(password, salt)
    db.set_setting("admin_password_salt", salt.hex())
    db.set_setting("admin_password_hash", pw_hash)


def verify_admin_password(password: str) -> bool:
    stored_hash = db.get_setting("admin_password_hash")
    salt_hex = db.get_setting("admin_password_salt")
    if not stored_hash or not salt_hex:
        # Default password if unconfigured: "admin"
        return password == "admin"
    salt = bytes.fromhex(salt_hex)
    computed = _hash(password, salt)
    return hmac.compare_digest(stored_hash, computed)


def create_session() -> str:
    token = secrets.token_hex(24)
    SESSION_TOKENS[token] = time.time() + TOKEN_TTL
    return token


def verify_session(token: str) -> bool:
    if not is_admin_configured():
        return True  # If no admin pass set yet, open access
    exp = SESSION_TOKENS.get(token)
    if not exp or time.time() > exp:
        SESSION_TOKENS.pop(token, None)
        return False
    return True


# ---- self-check ----
if __name__ == "__main__":
    db.init_db()
    set_admin_password("secret123")
    assert verify_admin_password("secret123")
    assert not verify_admin_password("wrong")
    token = create_session()
    assert verify_session(token)
    print("admin_auth self-check OK")
