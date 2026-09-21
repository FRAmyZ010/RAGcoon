"""Delete must remove orphan Project so re-upload of same title is allowed."""
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Avoid loading Settings/Postgres by importing Base only after dummy env if needed.
# Models import Base from database → set minimal env before imports.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")

from app.core.database import Base
from app.models.document import Document
from app.models.project import Project
from app.services.document_service import _purge_document_row_and_orphan_project


class DocumentDeleteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        project = Project(title="Unique Senior Project Title")
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        doc = Document(
            project_id=project.id,
            filename="demo.pdf",
            file_path="storage/documents/demo.pdf",
            title=project.title,
            status="COMPLETED",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        self.document = doc
        self.project_id = project.id

    def tearDown(self):
        self.db.close()

    def test_purge_removes_orphan_project(self):
        _purge_document_row_and_orphan_project(self.db, self.document)
        self.db.commit()

        self.assertIsNone(self.db.get(Document, self.document.id))
        self.assertIsNone(self.db.get(Project, self.project_id))

    def test_purge_keeps_project_if_other_documents_remain(self):
        extra = Document(
            project_id=self.project_id,
            filename="extra.pdf",
            file_path="storage/documents/extra.pdf",
            title="Unique Senior Project Title",
            status="COMPLETED",
        )
        self.db.add(extra)
        self.db.commit()
        self.db.refresh(extra)

        _purge_document_row_and_orphan_project(self.db, self.document)
        self.db.commit()

        self.assertIsNone(self.db.get(Document, self.document.id))
        self.assertIsNotNone(self.db.get(Project, self.project_id))
        self.assertIsNotNone(self.db.get(Document, extra.id))


if __name__ == "__main__":
    unittest.main()
