"""Invented category delete remaps documents; seed/Other stay locked."""
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
from app.models.rag_config import RagConfig  # noqa: F401 — register table
from app.rag.embedding.category_registry import (
    delete_invented_category,
    ensure_seeded,
    list_category_entries,
    register_invented,
)


class CategoryDeleteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_seeded(self.db)
        register_invented(self.db, ["Edge Computing"])

        project = Project(title="Category Remap Project")
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        self.doc_both = Document(
            project_id=project.id,
            filename="both.pdf",
            file_path="storage/documents/both.pdf",
            title=project.title,
            status="COMPLETED",
            keyword_groups="Web, Edge Computing",
        )
        self.doc_only = Document(
            project_id=project.id,
            filename="only.pdf",
            file_path="storage/documents/only.pdf",
            title="Only invented",
            status="COMPLETED",
            keyword_groups="Edge Computing",
        )
        self.db.add_all([self.doc_both, self.doc_only])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_list_marks_seed_locked(self):
        entries = {item["name"]: item for item in list_category_entries(self.db)}
        self.assertTrue(entries["Hardware"]["is_seed"])
        self.assertFalse(entries["Hardware"]["deletable"])
        self.assertTrue(entries["Edge Computing"]["deletable"])

    def test_cannot_delete_seed_or_other(self):
        with self.assertRaises(PermissionError):
            delete_invented_category(self.db, "Hardware")
        with self.assertRaises(PermissionError):
            delete_invented_category(self.db, "Other")

    def test_delete_invented_remaps_documents(self):
        result = delete_invented_category(self.db, "Edge Computing")
        self.assertEqual(result["deleted"], "Edge Computing")
        self.assertEqual(result["documents_updated"], 2)
        self.assertNotIn("Edge Computing", result["categories"])

        self.db.refresh(self.doc_both)
        self.db.refresh(self.doc_only)
        self.assertEqual(self.doc_both.keyword_groups, "Web")
        self.assertEqual(self.doc_only.keyword_groups, "Other")


if __name__ == "__main__":
    unittest.main()
