"""Data Processor & Post-Processing Module — Portable Web Agent."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def list_output_files() -> list[dict]:
    """List all files in the output directory with metadata."""
    if not OUTPUT_DIR.exists():
        return []
    files = []
    for p in sorted(OUTPUT_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True):
        if p.is_file():
            stat = p.stat()
            files.append({
                "name": p.name,
                "size_bytes": stat.st_size,
                "size_human": _human_size(stat.st_size),
                "modified_at": p.stat().st_mtime,
                "ext": p.suffix.lower(),
            })
    return files


def read_output_file(filename: str) -> dict:
    """Read contents of an output file safely."""
    path = (OUTPUT_DIR / filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل مورد نظر یافت نشد.")
    ext = path.suffix.lower()
    if ext in (".json", ".txt", ".csv", ".log"):
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"name": filename, "type": "text", "content": text, "ext": ext}
    elif ext in (".png", ".jpg", ".jpeg"):
        import base64
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"name": filename, "type": "image", "content": f"data:image/png;base64,{data}", "ext": ext}
    else:
        raise ValueError("فرمت فایل پشتیبانی نمی‌شود.")


def delete_output_file(filename: str) -> bool:
    """Delete an output file."""
    path = (OUTPUT_DIR / filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل مورد نظر یافت نشد.")
    path.unlink()
    return True


def json_to_csv(json_filename: str) -> str:
    """Convert an extracted JSON report file into CSV format."""
    path = (OUTPUT_DIR / json_filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل یافت نشد.")

    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages", [])
    if not messages and isinstance(data, list):
        messages = data

    if not messages:
        raise ValueError("داده‌ای برای تبدیل در فایل یافت نشد.")

    output = io.StringIO()
    # Flatten fields
    first = messages[0]
    headers = list(first.keys()) if isinstance(first, dict) else ["data"]

    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in messages:
        if isinstance(row, dict):
            # Clean newlines in values for cleaner CSV
            cleaned = {k: str(v).replace("\n", " ") if v is not None else "" for k, v in row.items()}
            writer.writerow(cleaned)

    csv_name = path.stem + ".csv"
    csv_path = OUTPUT_DIR / csv_name
    csv_path.write_text(output.getvalue(), encoding="utf-8-sig")
    return csv_name


def filter_data(json_filename: str, query: str = "", direction: str = "", kind: str = "") -> dict:
    """Filter extracted JSON dataset by search text, direction, or media type."""
    path = (OUTPUT_DIR / json_filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل یافت نشد.")

    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages", [])

    filtered = []
    for msg in messages:
        # Filter by text search
        if query:
            text = (msg.get("text") or "") + (msg.get("contact") or "") + (msg.get("media_details") or "")
            if not re.search(re.escape(query), text, re.IGNORECASE):
                continue
        # Filter by direction
        if direction and msg.get("direction") != direction:
            continue
        # Filter by kind
        if kind and msg.get("kind") != kind:
            continue
        filtered.append(msg)

    # Compute statistics
    stats = {
        "total": len(messages),
        "filtered_count": len(filtered),
        "incoming_count": sum(1 for m in filtered if m.get("direction") == "incoming"),
        "outgoing_count": sum(1 for m in filtered if m.get("direction") == "outgoing"),
        "kinds": {}
    }
    for m in filtered:
        k = m.get("kind", "other")
        stats["kinds"][k] = stats["kinds"].get(k, 0) + 1

    return {"stats": stats, "results": filtered}


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
