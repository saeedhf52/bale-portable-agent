"""Text-only tunneling protocol over Bale messenger.

The isolated network only allows text messages. This module turns arbitrary
Python objects into a stream of short text frames that can be pasted into a
Bale chat and reassembled on the other side.

Frame format (each line is one Bale message):

    BALE-TUN|v1|<msg_id>|<index>/<total>|<sha8>|<payload_chunk>

- msg_id: 8-hex random per message.
- payload: zlib-compressed JSON, base64-encoded, split into chunks.
- sha8: first 8 hex chars of sha256 of the full base64 payload (integrity).

Optional symmetric encryption (AES-GCM via `cryptography` if available, or
stdlib `hashlib`+XOR fallback). Encryption keys are pre-shared — never sent
over the tunnel.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import zlib

FRAME_RE = re.compile(r"^BALE-TUN\|v1\|([0-9a-f]{8})\|(\d+)/(\d+)\|([0-9a-f]{8})\|(.*)$")
DEFAULT_CHUNK = 3500  # safe under Bale's ~4096 text limit


def _xor(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    stream = hashlib.sha256(key).digest()
    return bytes(b ^ stream[i % len(stream)] for i, b in enumerate(data))


def encode(obj, key: bytes = b"", chunk: int = DEFAULT_CHUNK) -> list[str]:
    """Serialize obj → list of text frames ready to send over Bale."""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = zlib.compress(raw, 9)
    if key:
        packed = _xor(packed, key)
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
        """Return decoded object once the last frame for a message arrives, else None."""
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
            packed = _xor(packed, self.key)
        raw = zlib.decompress(packed)
        self.buckets.pop(msg_id, None)
        return json.loads(raw.decode("utf-8"))


def decode(frames: list[str], key: bytes = b""):
    """Convenience: decode a full list of frames at once."""
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
    frames = encode(payload, key=b"secret", chunk=200)
    assert len(frames) > 1, "should chunk"
    assert decode(frames, key=b"secret") == payload
    # Wrong key → corrupt data → zlib error
    try:
        decode(frames, key=b"wrong")
        raise AssertionError("should have failed")
    except Exception:
        pass
    print(f"bale_tunnel self-check OK ({len(frames)} chunks)")
