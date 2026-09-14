"""Web GUI Server & REST API for Bale Portable Agent (No external dependencies)."""
from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from pathlib import Path
import sys
import threading
import urllib.parse
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import automation_db as db
import automation_engine as engine
from bale_agent import probe_endpoint, endpoint_targets

UI_DIR = ROOT / "ui"
PORT = 8080


class AgentRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging to keep console clean

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path, content_type: str):
        if not file_path.is_file():
            self.send_error(404, "File Not Found")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/status":
            browser_ok = probe_endpoint(9222)
            self._send_json({"browser_active": browser_ok, "port": 9222})
        elif path == "/api/automations":
            if "id" in query:
                auto = db.get_automation(int(query["id"][0]))
                self._send_json(auto or {}, code=200 if auto else 404)
            else:
                self._send_json(db.list_automations())
        elif path == "/api/logs":
            self._send_json(db.list_logs())
        elif path == "/" or path == "/index.html":
            self._send_file(UI_DIR / "index.html", "text/html")
        elif path == "/style.css":
            self._send_file(UI_DIR / "style.css", "text/css")
        elif path == "/app.js":
            self._send_file(UI_DIR / "app.js", "application/javascript")
        else:
            self._send_file(UI_DIR / path.lstrip("/"), "text/plain")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        body = json.loads(raw_body) if raw_body else {}

        if path == "/api/automations":
            auto_id = body.get("id")
            name = body.get("name", "اتوماسیون جدید")
            desc = body.get("description", "")
            steps = body.get("steps", [])
            steps_json = json.dumps(steps, ensure_ascii=False) if isinstance(steps, list) else str(steps)

            saved_id = db.save_automation(name, desc, steps_json, auto_id)
            self._send_json({"success": True, "id": saved_id})

        elif path == "/api/automations/run":
            auto_id = body.get("id")
            steps = body.get("steps")

            if auto_id and not steps:
                auto = db.get_automation(int(auto_id))
                if not auto:
                    self._send_json({"success": False, "error": "اتوماسیون پیدا نشد."}, code=404)
                    return
                steps = json.loads(auto["steps_json"])

            if not steps:
                self._send_json({"success": False, "error": "گام‌های اتوماسیون خالی است."}, code=400)
                return

            try:
                results = engine.run_automation_steps(steps, port=9222)
                db.add_log(auto_id, "موفق", f"اجرای موفق {len(results)} گام", {"results": results})
                self._send_json({"success": True, "results": results})
            except Exception as exc:
                db.add_log(auto_id, "خطا", str(exc))
                self._send_json({"success": False, "error": str(exc)}, code=500)
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/automations":
            query = urllib.parse.parse_qs(parsed.query)
            if "id" in query:
                db.delete_automation(int(query["id"][0]))
                self._send_json({"success": True})
                return
        self.send_error(400, "Bad Request")


def main():
    db.init_db()
    server = HTTPServer(("127.0.0.1", PORT), AgentRequestHandler)
    print(f"Bale Portable Agent GUI active at http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    main()
