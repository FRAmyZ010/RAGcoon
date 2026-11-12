"""Postgres catalog listing for CATEGORY_LIST (skip-retrieval path)."""

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
    can_answer_from_catalog,
    catalog_unsupported_filters,
    format_catalog_context,
    list_projects_by_category,
    list_projects_from_filters,
)


class CategoryCatalogTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_seeded(self.db)

        p_iot = Project(
            title="IoT Watering System",
            academic_year=2023,
            advisor="Aj. Surapol Vorapatratorn",
            authors="Alice, Bob",
        )
        p_web = Project(
            title="Campus Web Portal",
            academic_year=2022,
            advisor="Dr. Mahamah Sebakor",
            authors="Carol",
        )
        p_iot2 = Project(
            title="Smart Farm Sensors",
            academic_year=2023,
            advisor="Aj. Surapol Vorapatratorn",
            authors="Dave",
        )
        self.db.add_all([p_iot, p_web, p_iot2])
        self.db.commit()
        for p in (p_iot, p_web, p_iot2):
            self.db.refresh(p)

        self.db.add_all(
            [
                Document(
                    project_id=p_iot.id,
                    filename="iot.pdf",
                    file_path="storage/iot.pdf",
                    title=p_iot.title,
                    keywords="ESP32, soil moisture",
                    keyword_groups="IoT, Hardware",
                    status="COMPLETED",
                ),
                Document(
                    project_id=p_web.id,
                    filename="web.pdf",
                    file_path="storage/web.pdf",
                    title=p_web.title,
                    keywords="React, PHP",
                    keyword_groups="Web",
                    status="COMPLETED",
                ),
                Document(
                    project_id=p_iot2.id,
                    filename="farm.pdf",
                    file_path="storage/farm.pdf",
                    title=p_iot2.title,
                    keywords="LoRa, sensor",
                    keyword_groups="IoT",
                    status="COMPLETED",
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_list_iot_category_with_metadata(self):
        result = list_projects_by_category(self.db, category="iot")
        self.assertEqual(result["matched_category"], "IoT")
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["projects"]), 2)
        titles = {item["title"] for item in result["projects"]}
        self.assertEqual(titles, {"IoT Watering System", "Smart Farm Sensors"})
        first = result["projects"][0]
        self.assertIn("authors", first)
        self.assertIn("advisor", first)
        self.assertIn("keywords", first)
        self.assertIn("categories", first)
        self.assertIn("year", first)

    def test_year_and_advisor_filters(self):
        result = list_projects_from_filters(
            self.db,
            {"category": "IoT", "year": "2023", "advisor": "Surapol"},
        )
        self.assertEqual(result["total"], 2)
        result_web_year = list_projects_from_filters(
            self.db,
            {"category": "IoT", "year": 2022},
        )
        self.assertEqual(result_web_year["total"], 0)

    def test_pagination(self):
        result = list_projects_by_category(self.db, category="IoT", offset=0, limit=1)
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["projects"]), 1)
        self.assertTrue(result["has_more"])
        page2 = list_projects_by_category(self.db, category="IoT", offset=1, limit=1)
        self.assertEqual(len(page2["projects"]), 1)
        self.assertFalse(page2["has_more"])
        self.assertNotEqual(result["projects"][0]["title"], page2["projects"][0]["title"])

    def test_fuzzy_suggest_unknown_category(self):
        result = list_projects_by_category(self.db, category="Iottt")
        self.assertIsNone(result["matched_category"])
        self.assertEqual(result["total"], 0)
        self.assertTrue(any(s.casefold() == "iot" for s in result["suggested_categories"]))
        context = format_catalog_context(result)
        self.assertIn("Suggested categories", context)
        self.assertNotIn("IoT Watering System", context)

    def test_can_answer_from_catalog_gate(self):
        self.assertTrue(can_answer_from_catalog({"category": "IoT", "year": "2023"}))
        self.assertEqual(catalog_unsupported_filters({"category": "IoT"}), [])
        self.assertFalse(can_answer_from_catalog({"category": "IoT", "target_domains": ["iot"]}))
        self.assertIn("target_domains", catalog_unsupported_filters({"category": "IoT", "target_domains": ["iot"]}))

    def test_build_category_list_retrieval_skips_vector_shape(self):
        payload = build_category_list_retrieval(
            normalized_query="senior projects in the IoT category",
            filters={"category": "IoT"},
            query_proc_seconds=0.01,
            db=self.db,
        )
        self.assertTrue(payload["catalog_mode"])
        self.assertTrue(payload["fast_path_used"])
        self.assertEqual(payload["intent"], "CATEGORY_LIST")
        self.assertEqual(payload["timing"]["rerank_seconds"], 0.0)
        self.assertIn("IoT Watering System", payload["catalog_context"])
        self.assertEqual(payload["retrieved_count"], 2)
        self.assertEqual(len(payload["catalog_citations"]), 2)
        self.assertEqual(payload["results"][0]["payload"]["source"], "postgres_catalog")


if __name__ == "__main__":
    unittest.main()
