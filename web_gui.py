"""Web GUI Server & REST API for Portable Web Agent (No external dependencies)."""
from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys
import urllib.parse
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import automation_db as db
import automation_engine as engine
import data_processor as dp
import skill_manager
from bale_agent import probe_endpoint, ensure_browser_ready

UI_DIR = ROOT / "ui"
PORT = 8080


class AgentRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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

    MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
            ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".csv": "text/csv"}

    def _send_file(self, file_path: Path):
        if not file_path.is_file():
            self.send_error(404, "File Not Found")
            return
        content = file_path.read_bytes()
        mime = self.MIME.get(file_path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text") or mime.endswith("json") or mime.endswith("javascript") else mime)
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
            active = probe_endpoint(9222)
            self._send_json({"browser_active": active, "port": 9222})
        elif path == "/api/automations":
            if "id" in query:
                auto = db.get_automation(int(query["id"][0]))
                self._send_json(auto or {}, code=200 if auto else 404)
            else:
                self._send_json(db.list_automations())
        elif path == "/api/templates":
            tpls = {k: {"name": v["name"], "description": v["description"], "steps": v["steps"]}
                    for k, v in engine.TEMPLATES.items()}
            self._send_json(tpls)
        elif path == "/api/logs":
            self._send_json(db.list_logs())
        elif path == "/api/skills":
            self._send_json(skill_manager.list_skills())
        elif path == "/api/knowledge/search":
            q = query.get("q", [""])[0]
            self._send_json(db.search_knowledge(q))

        # ── Output Data APIs ──
        elif path == "/api/outputs":
            if "name" in query:
                try:
                    self._send_json(dp.read_output_file(query["name"][0]))
                except Exception as e:
                    self._send_json({"error": str(e)}, code=404)
            else:
                self._send_json(dp.list_output_files())
        elif path == "/api/outputs/filter":
            fname = query.get("name", [""])[0]
            q = query.get("q", [""])[0]
            direction = query.get("direction", [""])[0]
            kind = query.get("kind", [""])[0]
            try:
                self._send_json(dp.filter_data(fname, q, direction, kind))
            except Exception as e:
                self._send_json({"error": str(e)}, code=400)

        elif path == "/" or path == "/index.html":
            self._send_file(UI_DIR / "index.html")
        else:
            self._send_file(UI_DIR / path.lstrip("/"))

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

        elif path == "/api/skills":
            try:
                name = body["name"]
                kind = body.get("kind", "recipe")
                content = body["content"]
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False)
                filepath = skill_manager.install_skill(name, kind, content)
                self._send_json({"success": True, "path": filepath})
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, code=400)

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
                import traceback
                tb_str = traceback.format_exc()
                db.add_log(auto_id, "خطا", str(exc))
                self._send_json({"success": False, "error": str(exc), "traceback": tb_str}, code=500)

        elif path == "/api/outputs/to_csv":
            fname = body.get("name")
            try:
                csv_name = dp.json_to_csv(fname)
                self._send_json({"success": True, "csv_name": csv_name})
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, code=400)

        elif path == "/api/browser/ensure":
            try:
                ready = ensure_browser_ready(port=9222)
                self._send_json({"success": ready, "message": "مرورگر آماده است." if ready else "مرورگر راه‌اندازی نشد."})
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, code=500)
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/automations":
            if "id" in query:
                db.delete_automation(int(query["id"][0]))
                self._send_json({"success": True})
                return
        elif parsed.path == "/api/skills":
            if "name" in query:
                removed = skill_manager.remove_skill(query["name"][0])
                self._send_json({"success": removed})
                return
        elif parsed.path == "/api/outputs":
            if "name" in query:
                try:
                    dp.delete_output_file(query["name"][0])
                    self._send_json({"success": True})
                    return
                except Exception as e:
                    self._send_json({"error": str(e)}, code=400)
                    return
        self.send_error(400, "Bad Request")


def main():
    db.init_db()
    server = HTTPServer(("127.0.0.1", PORT), AgentRequestHandler)
    print(f"Web Agent GUI: http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    main()
