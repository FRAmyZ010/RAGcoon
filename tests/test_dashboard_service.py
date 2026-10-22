"""Keyword aggregation for the dashboard service. No database."""
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

from app.services.dashboard_service import count_keywords


class DashboardServiceTests(unittest.TestCase):
    def test_counts_and_ranks_keywords(self):
        ranked = count_keywords(["IoT, Web", "iot", None, " Web , AI "], limit=2)
        self.assertEqual(ranked[0]["keyword"].casefold(), "iot")
        self.assertEqual(ranked[0]["count"], 2)
        self.assertEqual(ranked[1]["keyword"].casefold(), "web")
        self.assertEqual(len(ranked), 2)


if __name__ == "__main__":
    unittest.main()
