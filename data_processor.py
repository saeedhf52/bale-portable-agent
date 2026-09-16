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


def _extract_items(data: dict | list) -> list[dict]:
    """Helper to dynamically find item list inside any extracted JSON structure."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        # Table extraction format
        if "rows" in data and isinstance(data["rows"], list):
            return [x for x in data["rows"] if isinstance(x, dict)]
        # Bale messages format
        if "messages" in data and isinstance(data["messages"], list):
            return [x for x in data["messages"] if isinstance(x, dict)]
        # Scrape list format
        if "items" in data and isinstance(data["items"], list):
            return [x for x in data["items"] if isinstance(x, dict)]
        # Generic dict list search
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def json_to_csv(json_filename: str) -> str:
    """Convert an extracted JSON report file into CSV format."""
    path = (OUTPUT_DIR / json_filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل یافت نشد.")

    raw = json.loads(path.read_text(encoding="utf-8"))
    items = _extract_items(raw)

    if not items:
        raise ValueError("داده‌ای برای تبدیل در فایل یافت نشد.")

    output = io.StringIO()
    # Collect all unique field headers dynamically
    headers_set = {}
    for item in items:
        for k in item.keys():
            headers_set[k] = True
    headers = list(headers_set.keys())

    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in items:
        cleaned = {k: str(row.get(k, "")).replace("\n", " ") if row.get(k) is not None else "" for k in headers}
        writer.writerow(cleaned)

    csv_name = path.stem + ".csv"
    csv_path = OUTPUT_DIR / csv_name
    csv_path.write_text(output.getvalue(), encoding="utf-8-sig")
    return csv_name


def filter_data(json_filename: str, query: str = "", direction: str = "", kind: str = "") -> dict:
    """Filter extracted JSON dataset dynamically across all types (Tables, Bale, Crawls)."""
    path = (OUTPUT_DIR / json_filename).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
        raise ValueError("فایل یافت نشد.")

    raw = json.loads(path.read_text(encoding="utf-8"))
    items = _extract_items(raw)
    is_table = isinstance(raw, dict) and "rows" in raw

    filtered = []
    for item in items:
        # Text search across all dict values
        if query:
            all_str = " ".join(str(v) for v in item.values() if v is not None)
            if not re.search(re.escape(query), all_str, re.IGNORECASE):
                continue
        # Filter by direction (if present)
        if direction and item.get("direction") and item.get("direction") != direction:
            continue
        # Filter by kind (if present)
        if kind and item.get("kind") and item.get("kind") != kind:
            continue
        filtered.append(item)

    stats = {
        "total": len(items),
        "filtered_count": len(filtered),
        "incoming_count": sum(1 for m in filtered if m.get("direction") == "incoming"),
        "outgoing_count": sum(1 for m in filtered if m.get("direction") == "outgoing"),
        "is_table": is_table,
        "table_headers": raw.get("headers", []) if is_table else [],
        "kinds": {}
    }
    for m in filtered:
        k = m.get("kind", "other")
        stats["kinds"][k] = stats["kinds"].get(k, 0) + 1

    return {"stats": stats, "results": filtered, "raw": raw}


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
