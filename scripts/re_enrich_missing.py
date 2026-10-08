"""
Re-enrich missing/empty metadata for all projects in Qdrant collection.
Targets projects where summary is None or project_type is empty.
"""
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from qdrant_client.models import FieldCondition, Filter, MatchValue
from backend.app.rag.retrieval.config import COLLECTION_NAME, client
from backend.app.rag.embedding.enricher import extract_project_enrichment, infer_system_categories
from backend.app.rag.embedding.metadata_extractor import extract_project_metadata


def re_enrich_empty_projects():
    print(f"🚀 Scanning Qdrant Collection '{COLLECTION_NAME}' for empty projects...")
    start_total = time.perf_counter()

    # 1. Fetch all distinct source files and check their enrichment status
    next_offset = None
    project_sources: dict[str, dict] = {}

    while True:
        records, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
            offset=next_offset,
        )
        for r in records:
            p = r.payload or {}
            source = p.get("source")
            if not source:
                continue

            if source not in project_sources:
                project_sources[source] = {
                    "project_title": p.get("project_title") or p.get("title") or source,
                    "has_summary": bool(p.get("summary")),
                    "has_type": bool(p.get("project_type")),
                    "chunks": [],
                }

            page_num = p.get("page_number", 999)
            text = p.get("content", "")
            if page_num <= 10 and text:
                project_sources[source]["chunks"].append((page_num, text))

        if next_offset is None:
            break

    # 2. Filter for projects that are empty (missing summary or missing project_type)
    empty_projects = {
        src: data for src, data in project_sources.items()
        if not data["has_summary"] or not data["has_type"]
    }

    print(f"📦 Total projects: {len(project_sources)} | Found {len(empty_projects)} empty project(s) needing enrichment.\n")

    if not empty_projects:
        print("🎉 All projects are already fully enriched! Nothing to do.")
        return

    # 3. Process each empty project
    for idx, (source, data) in enumerate(empty_projects.items(), 1):
        t0 = time.perf_counter()
        p_title = data["project_title"]
        print(f"[{idx}/{len(empty_projects)}] Enriching: {p_title}")
        print(f"   📄 Source: {source}")

        # Sort chunks by page number and combine
        data["chunks"].sort(key=lambda x: x[0])
        combined_text = "\n\n".join([chunk[1] for chunk in data["chunks"]])
        print(f"   📑 Gathered {len(data['chunks'])} chunks ({len(combined_text)} characters)")

        # Extract program and school
        meta = extract_project_metadata(combined_text, filename=source)
        program = meta.get("program") or "Computer Engineering"
        school = meta.get("school") or "Applied Digital Technology"

        # LLM Enrichment with 120s timeout
        enrichment = extract_project_enrichment(combined_text, project_title=p_title, timeout=120)

        # Fallback safeguard: if project_type is still empty, infer from rule-based
        proj_types = enrichment.get("project_type") or []
        if not proj_types:
            proj_types = infer_system_categories(combined_text, p_title)

        payload_update = {
            "program": program,
            "school": school,
            "summary": enrichment.get("summary"),
            "project_type": proj_types,
            "key_technologies": enrichment.get("key_technologies", []),
            "target_problem": enrichment.get("target_problem"),
        }

        # Update Qdrant
        src_filter = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        client.set_payload(
            collection_name=COLLECTION_NAME,
            payload=payload_update,
            points=src_filter,
        )

        elapsed = time.perf_counter() - t0
        print(f"   ✨ Types: {proj_types}")
        print(f"   ✨ Tech: {enrichment.get('key_technologies', [])}")
        print(f"   ✨ Summary: {(enrichment.get('summary') or 'None')[:85]}...")
        print(f"   ✅ Updated in {elapsed:.2f}s\n")

    total_time = time.perf_counter() - start_total
    print(f"🎉 Complete! Successfully re-enriched {len(empty_projects)} projects in {total_time:.2f}s.")


if __name__ == "__main__":
    re_enrich_empty_projects()
