"""Prescreen replies that must not call retrieval."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.prescreen import prescreen_reply


class PrescreenTests(unittest.TestCase):
    def test_greeting_small_talk_and_noise_skip_retrieval(self):
        self.assertIn("Hello", prescreen_reply("สวัสดี"))
        self.assertIn("assistant", prescreen_reply("คุณคือใคร"))
        self.assertIn("couldn't understand", prescreen_reply("asdfghjkl"))
        self.assertIn("only answer", prescreen_reply("วิธีทำผัดไทย"))
        self.assertIn("Which project", prescreen_reply("ขอข้อมูลเพิ่มเติม"))

    def test_project_questions_go_to_rag(self):
        self.assertIsNone(prescreen_reply("PLC คืออะไร"))
        self.assertIsNone(prescreen_reply("สวัสดีจ้า ช่วยสรุปโปรเจค Petfeeder ให้หน่อย"))
        self.assertIsNone(prescreen_reply("โปเจค prefeeder คิออะไล"))


if __name__ == "__main__":
    unittest.main()
