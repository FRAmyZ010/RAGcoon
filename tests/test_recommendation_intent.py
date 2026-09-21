"""
Test Suite: Dedicated RECOMMENDATION Intent with Evidence Coverage & Diversity
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.llm_query_processor import process_query_with_llm
from app.rag.retrieval.prompt import answer_question, stream_answer_question
from app.rag.retrieval.service import search_with_details
from app.rag.retrieval.session_manager import session_manager


def test_recommendation_intent_detection():
    print("\n--- 1. Testing Intent Detection for Recommendation Queries ---")
    queries = [
        "Could you recommend some projects?",
        "แนะนำโปรเจกต์ที่น่าสนใจและเอาไปต่อยอดได้หน่อย",
        "Suggest some good computer engineering projects",
        "มีหัวข้อโปรเจกต์ไหนน่าสนใจเอาไปทำเป็น Senior Project บ้าง",
    ]
    for q in queries:
        norm_q, filters, intent = process_query_with_llm(q)
        print(f"Query: '{q}' -> Intent: {intent} | Filters: {filters}")
        assert intent == "RECOMMENDATION", f"Expected RECOMMENDATION, got {intent} for '{q}'"
    print("✅ Intent Detection for RECOMMENDATION passed!")


def test_recommendation_retrieval_diversity():
    print("\n--- 2. Testing Candidate Retrieval Diversity for RECOMMENDATION ---")
    q = "Could you recommend some projects?"
    details = search_with_details(q)
    results = details.get("results", [])
    distinct_projects = {
        r.get("payload", {}).get("project_title") or r.get("payload", {}).get("source")
        for r in results
    }
    print(f"Retrieved {len(results)} chunks spanning {len(distinct_projects)} distinct projects:")
    for proj in distinct_projects:
        print(f"  • {proj}")

    assert len(distinct_projects) >= 4, f"Expected at least 4 distinct projects, got {len(distinct_projects)}"
    print("✅ Candidate Retrieval Diversity for RECOMMENDATION passed!")


def test_recommendation_streaming_generation():
    print("\n--- 3. Testing Real-Time Streaming RAG Generation for RECOMMENDATION ---")
    session_id = "test-rec-stream-session"
    session_manager.clear_session(session_id)

    q = "Could you recommend some projects?"
    full_tokens = []
    citations_received = []

    for event in stream_answer_question(q, session_id=session_id):
        event_type = event.get("event")
        data = event.get("data", {})
        if event_type == "metadata":
            print(f"Metadata Intent: {data.get('intent')} | Sources: {len(data.get('sources', []))}")
            assert data.get("intent") == "RECOMMENDATION"
        elif event_type == "token":
            full_tokens.append(data.get("token", ""))
        elif event_type == "done":
            citations_received = data.get("citations", [])

    full_answer = "".join(full_tokens)
    print(f"\nGenerated Answer Sample:\n{full_answer[:300]}...\n")
    print(f"Citations count: {len(citations_received)}")

    assert len(citations_received) >= 3, "Expected at least 3 project citations"
    assert len(full_answer) > 200, "Answer too short"
    print("✅ Streaming Recommendation Generation passed!")


if __name__ == "__main__":
    test_recommendation_intent_detection()
    test_recommendation_retrieval_diversity()
    test_recommendation_streaming_generation()
