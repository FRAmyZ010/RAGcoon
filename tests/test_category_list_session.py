"""CATEGORY_LIST session pagination state (last_category_list)."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")

from app.core.database import Base
from app.models.document import Document
from app.models.project import Project
from app.models.rag_config import RagConfig  # noqa: F401
from app.rag.embedding.category_registry import ensure_seeded
from app.rag.retrieval.category_catalog import (
    build_category_list_retrieval,
    looks_like_category_list_follow_up,
)
from app.rag.retrieval.session_manager import SessionChatManager, session_manager


class CategoryListSessionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_seeded(self.db)

        for i in range(3):
            project = Project(
                title=f"IoT Project {i}",
                academic_year=2023,
                advisor="Aj. Surapol",
                authors=f"Author {i}",
            )
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            self.db.add(
                Document(
                    project_id=project.id,
                    filename=f"iot{i}.pdf",
                    file_path=f"storage/iot{i}.pdf",
                    title=project.title,
                    keywords="ESP32",
                    keyword_groups="IoT",
                    status="COMPLETED",
                )
            )
        self.db.commit()

        self.sid = "test-category-list-session"
        session_manager.clear_session(self.sid)

    def tearDown(self):
        session_manager.clear_session(self.sid)
        self.db.close()

    def test_follow_up_heuristic(self):
        self.assertTrue(looks_like_category_list_follow_up("ขอเพิ่ม"))
        self.assertTrue(looks_like_category_list_follow_up("next page"))
        self.assertTrue(looks_like_category_list_follow_up("show more"))
        self.assertFalse(looks_like_category_list_follow_up("Which senior projects are in the IoT category?"))

    def test_session_state_roundtrip(self):
        mgr = SessionChatManager(max_turns=3)
        mgr.set_last_category_list(
            self.sid,
            {"category": "IoT", "next_offset": 10, "filters": {"category": "IoT"}, "has_more": True},
        )
        state = mgr.get_last_category_list(self.sid)
        self.assertEqual(state["category"], "IoT")
        self.assertEqual(state["next_offset"], 10)
        mgr.clear_last_category_list(self.sid)
        self.assertIsNone(mgr.get_last_category_list(self.sid))

    def test_build_retrieval_updates_session_and_paginates(self):
        page1 = build_category_list_retrieval(
            normalized_query="senior projects in the IoT category",
            filters={"category": "IoT"},
            offset=0,
            limit=2,
            db=self.db,
            session_id=self.sid,
        )
        self.assertTrue(page1["catalog"]["has_more"])
        self.assertEqual(len(page1["catalog"]["projects"]), 2)
        state = session_manager.get_last_category_list(self.sid)
        self.assertEqual(state["category"], "IoT")
        self.assertEqual(state["next_offset"], 2)
        self.assertTrue(state["has_more"])

        page2 = build_category_list_retrieval(
            normalized_query=state["normalized_query"],
            filters=state["filters"],
            offset=state["next_offset"],
            limit=2,
            db=self.db,
            session_id=self.sid,
        )
        self.assertEqual(len(page2["catalog"]["projects"]), 1)
        self.assertFalse(page2["catalog"]["has_more"])
        titles1 = {p["title"] for p in page1["catalog"]["projects"]}
        titles2 = {p["title"] for p in page2["catalog"]["projects"]}
        self.assertTrue(titles1.isdisjoint(titles2))
        state2 = session_manager.get_last_category_list(self.sid)
        self.assertEqual(state2["next_offset"], 3)
        self.assertFalse(state2["has_more"])


if __name__ == "__main__":
    unittest.main()
