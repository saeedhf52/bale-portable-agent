"""SQLite database manager for Bale Portable Agent automations."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "agent.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                automation_id INTEGER,
                status TEXT NOT NULL,
                message TEXT,
                details_json TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Insert default Bale Export automation if none exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM automations")
        if cursor.fetchone()[0] == 0:
            default_steps = [
                {"action": "bale_export", "count": 10, "timeout": 20}
            ]
            cursor.execute(
                "INSERT INTO automations (name, description, steps_json) VALUES (?, ?, ?)",
                ("استخراج ۱۰ پیام اخیر بله", "استخراج خودکار پیام‌های 10 مخاطب اخیر بله وب", json.dumps(default_steps, ensure_ascii=False))
            )
            conn.commit()


def list_automations():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM automations ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_automation(auto_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM automations WHERE id = ?", (auto_id,)).fetchone()
        return dict(row) if row else None


def save_automation(name: str, description: str, steps_json: str, auto_id: int | None = None):
    with get_db() as conn:
        if auto_id:
            conn.execute(
                "UPDATE automations SET name = ?, description = ?, steps_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, description, steps_json, auto_id)
            )
            return auto_id
        else:
            cursor = conn.execute(
                "INSERT INTO automations (name, description, steps_json) VALUES (?, ?, ?)",
                (name, description, steps_json)
            )
            return cursor.lastrowid


def delete_automation(auto_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM automations WHERE id = ?", (auto_id,))


def add_log(automation_id: int | None, status: str, message: str, details: dict | None = None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO logs (automation_id, status, message, details_json) VALUES (?, ?, ?, ?)",
            (automation_id, status, message, json.dumps(details or {}, ensure_ascii=False))
        )


def list_logs(limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT l.*, a.name as automation_name FROM logs l LEFT JOIN automations a ON l.automation_id = a.id ORDER BY l.executed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
