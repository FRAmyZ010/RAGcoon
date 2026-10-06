"""
Enrich Existing Qdrant Collection with Structured Metadata:
  1. Detects distinct projects in Qdrant.
  2. Extracts Program ('Computer Engineering') and School.
  3. Uses local LLM (Ollama) to extract:
     - summary (1-2 sentences)
     - project_type (categories)
     - key_technologies (tech stack list)
     - target_problem (problem statement)
  4. Updates Qdrant points with set_payload.
  5. Deletes legacy noisy fields (keywords, committee, total_pages) with delete_payload.
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
from backend.app.rag.embedding.enricher import extract_project_enrichment
from backend.app.rag.embedding.metadata_extractor import extract_project_metadata


def run_enrichment():
    print(f"🚀 Starting Metadata Enrichment for Qdrant Collection: {COLLECTION_NAME}")
    start_time = time.perf_counter()

    # 1. Fetch all distinct source files and their sample abstract text
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
                    "author": p.get("author"),
                    "advisor": p.get("advisor"),
                    "year": p.get("year"),
                    "chunks": [],
                }

            page_num = p.get("page_number", 999)
            text = p.get("content", "")
            if page_num <= 8 and text:
                project_sources[source]["chunks"].append((page_num, text))

        if next_offset is None:
            break

    print(f"📦 Found {len(project_sources)} distinct project(s) in Qdrant.")

    # 2. Enrich each project
    for idx, (source, data) in enumerate(project_sources.items(), 1):
        p_title = data["project_title"]
        print(f"\n[{idx}/{len(project_sources)}] Processing: {p_title} ({source})")

        # Sort chunks by page number
        data["chunks"].sort(key=lambda x: x[0])
        combined_text = "\n\n".join([chunk[1] for chunk in data["chunks"]])

        # Extract program and school
        meta = extract_project_metadata(combined_text, filename=source)
        program = meta.get("program") or "Computer Engineering"
        school = meta.get("school") or "Applied Digital Technology"

        # LLM Enrichment
        print("   🧠 Running LLM enrichment (summary, type, tech, problem)...")
        enrichment = extract_project_enrichment(combined_text, project_title=p_title)

        payload_update = {
            "program": program,
            "school": school,
            "summary": enrichment.get("summary"),
            "project_type": enrichment.get("project_type", []),
            "key_technologies": enrichment.get("key_technologies", []),
            "target_problem": enrichment.get("target_problem"),
        }

        print(f"   ✨ Program: {program}")
        print(f"   ✨ Summary: {enrichment.get('summary')[:90]}..." if enrichment.get('summary') else "   ⚠️ Summary: None")
        print(f"   ✨ Tech: {enrichment.get('key_technologies')}")
        print(f"   ✨ Type: {enrichment.get('project_type')}")

        # Update Qdrant
        src_filter = Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])

        client.set_payload(
            collection_name=COLLECTION_NAME,
            payload=payload_update,
            points=src_filter,
        )

        # Delete legacy field: keywords (keeping committee and total_pages intact)
        try:
            client.delete_payload(
                collection_name=COLLECTION_NAME,
                keys=["keywords"],
                points=src_filter,
            )
        except Exception as e:
            print(f"   ⚠️ Could not delete legacy keys: {e}")

        print("   ✅ Qdrant payload updated successfully.")

    total_elapsed = time.perf_counter() - start_time
    print(f"\n🎉 Finished enriching {len(project_sources)} projects in {total_elapsed:.2f}s!")


if __name__ == "__main__":
    run_enrichment()
