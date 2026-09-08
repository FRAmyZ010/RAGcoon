import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from .config import DEFAULT_TOP_K, DEFAULT_TOP_N
from .extractor import QueryFilterProcessor
from .filters import build_qdrant_filter
from .normalizer import normalize_user_query as normalize_query
from .rerank import rerank
from .semantic import semantic_search


from .llm_query_processor import process_query_with_llm


def _get_routing_params(intent: str) -> tuple[int, int]:
    """Return adaptive (top_k, top_n) based on query intent."""
    if intent in {"EXPLORATORY", "COMPARISON"}:
        return 30, 10
    elif intent == "DEEP_DIVE":
        return 20, 8
    elif intent == "CODE":
        return 20, 7
    return DEFAULT_TOP_K, DEFAULT_TOP_N


def search(query: str) -> list[str]:
    print("\n" + "=" * 60)
    print("ORIGINAL QUERY:", query)

    # 1. Use LLM Query Normalizer & Filter Extractor & Intent Classifier
    clean_query, filters, intent = process_query_with_llm(query)
    top_k, top_n = _get_routing_params(intent)
    print("NORMALIZED / CLEAN QUERY:", clean_query)
    print("INTENT:", intent)
    print("FILTERS:", filters)

    qdrant_filter = build_qdrant_filter(filters)
    print("QDRANT FILTER:", qdrant_filter)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    if not results:
        print("No results after semantic + filter")
        return []

    print(f"Retrieved (before rerank): {len(results)} docs")

    reranked = rerank(clean_query, results, top_n)
    print(f"Top after rerank: {len(reranked)} docs")

    return [result["text"] for result in reranked]


def search_with_details(query: str) -> dict:
    """Search and return detailed results with scores, timing, and dynamic routing intent."""
    total_start = time.perf_counter()
    try:
        print("\n" + "=" * 60)
        print("ORIGINAL QUERY:", query)

        # 1. Use LLM Query Normalizer & Filter Extractor & Intent Classifier
        query_proc_start = time.perf_counter()
        normalized_query, filters, intent = process_query_with_llm(query)
        query_proc_seconds = time.perf_counter() - query_proc_start
        clean_query = normalized_query
        top_k, top_n = _get_routing_params(intent)
        print("NORMALIZED / CLEAN QUERY:", clean_query)
        print("INTENT:", intent)
        print("FILTERS:", filters)

        retrieval_start = time.perf_counter()
        results = semantic_search(clean_query, top_k, metadata_filters=filters)
        retrieval_seconds = time.perf_counter() - retrieval_start
        print(f"Retrieved (before rerank): {len(results)} results")

        if not results:
            print("No results after semantic + filter")
            total_seconds = time.perf_counter() - total_start
            return {
                "results": [],
                "errors": [],
                "timing": {
                    "query_proc_seconds": query_proc_seconds,
                    "retrieval_seconds": retrieval_seconds,
                    "rerank_seconds": 0.0,
                    "total_seconds": total_seconds,
                },
                "normalized_query": normalized_query,
                "filters": filters,
                "intent": intent,
                "query_variants": [],
                "retrieved_count": 0,
            }

        try:
            rerank_start = time.perf_counter()
            reranked = rerank(clean_query, results, top_n)
            rerank_seconds = time.perf_counter() - rerank_start
            print(f"\n🎯 [RERANK] Top {len(reranked)} Results (Full Chunks):")
            print("=" * 70)
            for i, result in enumerate(reranked, 1):
                payload = result.get("payload", {})
                score = result.get("score", 0.0)
                source = payload.get("source", "Unknown")
                page = payload.get("page_number", "?")
                title = payload.get("project_title") or payload.get("title", "-")
                advisor = payload.get("advisor", "-")
                author = payload.get("author", "-")

                print(f"📄 Chunk #{i} | Rerank Score: {score:.4f}")
                print(f"   ├─ Source: {source} (Page {page})")
                print(f"   ├─ Title: {title}")
                print(f"   ├─ Author: {author} | Advisor: {advisor}")
                print("   └─ Content:")
                clean_text = result["text"].replace("\r\n", "\n").replace("\r", "\n")
                for line in clean_text.strip().split("\n"):
                    print(f"      {line}")
                print("-" * 70)
        except (TypeError, ValueError, RuntimeError, AttributeError) as e:
            print(f"Error during reranking: {e}")
            rerank_seconds = 0.0
            reranked = results[:top_n]  # Fallback to top semantic results

        total_seconds = time.perf_counter() - total_start
        return {
            "results": reranked,
            "filters": filters,
            "intent": intent,
            "errors": [],
            "timing": {
                "query_proc_seconds": query_proc_seconds,
                "retrieval_seconds": retrieval_seconds,
                "rerank_seconds": rerank_seconds,
                "total_seconds": total_seconds,
            },
            "normalized_query": normalized_query,
            "query_variants": [],
            "retrieved_count": len(results),
        }
    except (TypeError, ValueError, RuntimeError, AttributeError) as exc:
        error_msg = str(exc)
        print(f"Error in search_with_details: {error_msg}")
        total_seconds = time.perf_counter() - total_start
        return {
            "results": [],
            "errors": [error_msg],
            "intent": "FACTOID",
            "timing": {
                "query_proc_seconds": 0.0,
                "retrieval_seconds": 0.0,
                "rerank_seconds": 0.0,
                "total_seconds": total_seconds,
            },
            "normalized_query": query,
            "query_variants": [],
            "retrieved_count": 0,
        }


def hybrid_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    top_n: int = DEFAULT_TOP_N,
    metadata_filters: dict | None = None,
) -> list[dict]:
    """Compatibility wrapper for the current semantic-search plus rerank pipeline."""
    clean_query, filters, _ = process_query_with_llm(query)

    if metadata_filters:
        filters.update(metadata_filters)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    return rerank(clean_query, results, top_n)
