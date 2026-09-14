import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import bale_agent as agent


class ExportTests(unittest.TestCase):
    def test_calendar_known_dates(self):
        for gregorian, expected in [("2026-09-14", "1405/06/23"), ("2026-03-21", "1405/01/01"), ("2025-03-20", "1403/12/30")]:
            self.assertEqual(agent.jalali_date(dt.date.fromisoformat(gregorian)), expected)

    def test_cdp_refuses_remote_and_spoofed_hosts(self):
        for url in ["ws://example.org:9222/x", "ws://127.0.0.1.evil/x", "ws://user:pass@localhost/x", "wss://localhost/x"]:
            with self.assertRaises(agent.AgentError):
                agent.local_url(url, {"ws"})
        agent.local_url("ws://127.0.0.1:9222/devtools/page/1", {"ws"})

    def test_only_bale_page_targets_are_selected(self):
        def target(url, name):
            return {"type": "page", "id": name, "url": url, "webSocketDebuggerUrl": "ws://localhost/x"}
        valid = target("https://web.bale.ai/chat", "correct")
        self.assertEqual(agent.select_target([target("https://web.bale.ai.evil/chat", "fake"), valid]), valid)
        with self.assertRaises(agent.AgentError):
            agent.select_target([valid, target("https://web.bale.ai/chat?uid=1", "duplicate")])

    def test_outgoing_reply_text_not_replaced_by_quote(self):
        message = {"epoch_ms": "1789192448236", "direction": "outgoing", "text": "سلام ممنون.\nتوی این دو فاکتور نبود", "kind": "text", "reply_to": "1481.pdf"}
        result = agent.finalize_record({"name": "مخاطب", "index": 1}, message)
        self.assertEqual(result["time"], "09:24")
        self.assertEqual(result["jalali_date"], "1405/06/21")
        self.assertNotEqual(result["text"], result["reply_to"])

    def test_export_persian_roundtrip_and_no_overwrite(self):
        report = {"complete": False, "requested_count": 2, "collected_at": "2026-09-14", "errors": ["one failed"], "messages": [
            {"contact": "نام 🕊️", "jalali_date": "1405/06/23", "time": "08:22", "direction": "incoming", "text": "سلام 👋\nمتن کامل", "kind": "text"}
        ]}
        with tempfile.TemporaryDirectory() as folder:
            txt, js = agent.save_report(report, folder)
            self.assertTrue(txt.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertIn("سلام 👋", txt.read_text(encoding="utf-8-sig"))
            self.assertEqual(json.loads(js.read_text(encoding="utf-8")), report)
            again, _ = agent.save_report(report, folder)
            self.assertNotEqual(txt, again)

    def test_pinned_old_chat_does_not_displace_newer_unpinned(self):
        rows = [
            {"name": "old pin", "index": 0, "kind": "personal", "pinned": True, "self": False, "join_only": False},
            {"name": "self", "index": 1, "kind": "personal", "pinned": True, "self": True, "join_only": False},
            {"name": "new", "index": 2, "kind": "personal", "pinned": False, "self": False, "join_only": False},
            {"name": "joined", "index": 3, "kind": "personal", "pinned": False, "self": False, "join_only": True},
            {"name": "second", "index": 4, "kind": "personal", "pinned": False, "self": False, "join_only": False},
        ]
        state = {"personal": True, "rows": rows, "scroll_top": 0, "at_bottom": True}
        with patch.object(agent, "adapter_call", return_value=state):
            selected = agent.collect_rows(None, 2, 2)
        self.assertEqual([r["name"] for r in selected], ["old pin", "new", "second"])


if __name__ == "__main__":
    unittest.main()
