"""Text-only tunneling protocol over Bale messenger.

The isolated network only allows text messages. This module turns arbitrary
Python objects into a stream of short text frames that can be pasted into a
Bale chat and reassembled on the other side.

Frame format (each line is one Bale message):

    BALE-TUN|v1|<msg_id>|<index>/<total>|<sha8>|<payload_chunk>

- msg_id: 8-hex random per message.
- payload: zlib-compressed JSON, optionally authenticated-encrypted, base64.
- sha8: first 8 hex chars of sha256 of the full base64 payload (integrity).

When a key is provided, payload is authenticated-encrypted:
    nonce(16) || SHA256-CTR-XOR-ciphertext || HMAC-SHA256-tag(16)
Encrypt-then-MAC pattern; pure stdlib, no external crypto library required.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import zlib

FRAME_RE = re.compile(r"^BALE-TUN\|v1\|([0-9a-f]{8})\|(\d+)/(\d+)\|([0-9a-f]{8})\|(.*)$")
DEFAULT_CHUNK = 3500  # safe under Bale's ~4096 text limit
_NONCE_LEN = 16
_TAG_LEN = 16


def _derive(key: bytes, label: bytes) -> bytes:
    """HKDF-like: derive a subkey for encryption or MAC."""
    return hashlib.sha256(b"BALE-TUN-v1|" + label + b"|" + key).digest()


def _stream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """SHA256-CTR keystream: SHA256(enc_key || nonce || counter_be) blocks."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(enc_key + nonce + counter.to_bytes(8, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _encrypt(data: bytes, key: bytes) -> bytes:
    enc_key = _derive(key, b"enc")
    mac_key = _derive(key, b"mac")
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = bytes(a ^ b for a, b in zip(data, _stream(enc_key, nonce, len(data))))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()[:_TAG_LEN]
    return nonce + ciphertext + tag


def _decrypt(blob: bytes, key: bytes) -> bytes:
    if len(blob) < _NONCE_LEN + _TAG_LEN:
        raise ValueError("Ciphertext too short")
    nonce = blob[:_NONCE_LEN]
    tag = blob[-_TAG_LEN:]
    ciphertext = blob[_NONCE_LEN:-_TAG_LEN]
    mac_key = _derive(key, b"mac")
    expected = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()[:_TAG_LEN]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("MAC verification failed — wrong key or tampered payload")
    enc_key = _derive(key, b"enc")
    return bytes(a ^ b for a, b in zip(ciphertext, _stream(enc_key, nonce, len(ciphertext))))


def encode(obj, key: bytes = b"", chunk: int = DEFAULT_CHUNK) -> list[str]:
    """Serialize obj → list of text frames ready to send over Bale."""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = zlib.compress(raw, 9)
    if key:
        packed = _encrypt(packed, key)
    b64 = base64.b64encode(packed).decode("ascii")
    sha8 = hashlib.sha256(b64.encode()).hexdigest()[:8]
    msg_id = os.urandom(4).hex()
    parts = [b64[i:i + chunk] for i in range(0, len(b64), chunk)] or [""]
    total = len(parts)
    return [f"BALE-TUN|v1|{msg_id}|{i+1}/{total}|{sha8}|{p}" for i, p in enumerate(parts)]


class Reassembler:
    """Collects frames across turns and yields decoded objects."""

    def __init__(self, key: bytes = b""):
        self.key = key
        self.buckets: dict[str, dict] = {}

    def feed(self, line: str):
        m = FRAME_RE.match(line.strip())
        if not m:
            return None
        msg_id, idx, total, sha8, chunk = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        bucket = self.buckets.setdefault(msg_id, {"total": total, "sha8": sha8, "parts": {}})
        bucket["parts"][idx] = chunk
        if len(bucket["parts"]) < total:
            return None
        b64 = "".join(bucket["parts"][i] for i in range(1, total + 1))
        if hashlib.sha256(b64.encode()).hexdigest()[:8] != sha8:
            self.buckets.pop(msg_id, None)
            raise ValueError(f"Checksum mismatch for msg {msg_id}")
        packed = base64.b64decode(b64)
        if self.key:
            packed = _decrypt(packed, self.key)
        raw = zlib.decompress(packed)
        self.buckets.pop(msg_id, None)
        return json.loads(raw.decode("utf-8"))


def decode(frames: list[str], key: bytes = b""):
    r = Reassembler(key)
    result = None
    for f in frames:
        maybe = r.feed(f)
        if maybe is not None:
            result = maybe
    if result is None:
        raise ValueError("Incomplete frame set")
    return result


# ---- self-check ----
if __name__ == "__main__":
    payload = {"cmd": "run_skill", "name": "demo", "args": {"x": list(range(200))}}
    # Encrypted round-trip
    frames = encode(payload, key=b"secret", chunk=200)
    assert len(frames) > 1, "should chunk"
    assert decode(frames, key=b"secret") == payload
    # Wrong key → MAC failure
    try:
        decode(frames, key=b"wrong")
        raise AssertionError("should have failed")
    except ValueError as e:
        assert "MAC" in str(e) or "wrong key" in str(e).lower()
    # Unencrypted round-trip
    frames2 = encode(payload, chunk=200)
    assert decode(frames2) == payload
    # Tamper detection
    bad = frames[0][:-5] + "AAAAA"
    try:
        decode([bad] + frames[1:], key=b"secret")
        raise AssertionError("should have failed on tamper")
    except ValueError:
        pass
    print(f"bale_tunnel self-check OK ({len(frames)} chunks, AES-like AE + HMAC)")
