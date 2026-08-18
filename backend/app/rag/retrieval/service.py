import time
from typing import Dict, List, Optional

from .config import DEFAULT_TOP_K, DEFAULT_TOP_N
from .filters import build_qdrant_filter
from .query import extract_query_and_filters, normalize_query
from .rerank import rerank
from .semantic import semantic_search


def search(query: str) -> List[str]:
    print("\n" + "=" * 60)
    print("ORIGINAL QUERY:", query)

    normalized_query = normalize_query(query)
    print("NORMALIZED QUERY:", normalized_query)

    clean_query, filters = extract_query_and_filters(normalized_query)

    print("CLEAN QUERY:", clean_query)
    print("FILTERS:", filters)

    qdrant_filter = build_qdrant_filter(filters)
    print("QDRANT FILTER:", qdrant_filter)

    results = semantic_search(clean_query, DEFAULT_TOP_K, metadata_filters=filters)
    if not results:
        print("No results after semantic + filter")
        return []

    print(f"Retrieved (before rerank): {len(results)} docs")

    reranked = rerank(clean_query, results, DEFAULT_TOP_N)
    print(f"Top after rerank: {len(reranked)} docs")

    return [result["text"] for result in reranked]


def search_with_details(query: str) -> dict:
    """Search and return detailed results with scores and timing."""
    total_start = time.perf_counter()
    try:
        print("\n" + "=" * 60)

        normalized_query = normalize_query(query)
        clean_query, filters = extract_query_and_filters(normalized_query)

        retrieval_start = time.perf_counter()
        results = semantic_search(clean_query, DEFAULT_TOP_K, metadata_filters=filters)
        retrieval_seconds = time.perf_counter() - retrieval_start

        if not results:
            print("No results after semantic + filter")
            total_seconds = time.perf_counter() - total_start
            return {
                "results": [],
                "errors": [],
                "timing": {
                    "retrieval_seconds": retrieval_seconds,
                    "rerank_seconds": 0.0,
                    "total_seconds": total_seconds,
                },
                "normalized_query": normalized_query,
                "query_variants": [],
                "retrieved_count": 0,
            }

        rerank_start = time.perf_counter()
        reranked = rerank(clean_query, results, DEFAULT_TOP_N)
        rerank_seconds = time.perf_counter() - rerank_start

        total_seconds = time.perf_counter() - total_start
        return {
            "results": reranked,
            "errors": [],
            "timing": {
                "retrieval_seconds": retrieval_seconds,
                "rerank_seconds": rerank_seconds,
                "total_seconds": total_seconds,
            },
            "normalized_query": normalized_query,
            "query_variants": [],
            "retrieved_count": len(results),
        }
    except Exception as exc:
        error_msg = str(exc)
        print(f"Error in search_with_details: {error_msg}")
        total_seconds = time.perf_counter() - total_start
        return {
            "results": [],
            "errors": [error_msg],
            "timing": {
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
    metadata_filters: Optional[Dict] = None,
) -> List[Dict]:
    """Compatibility wrapper for the current semantic-search plus rerank pipeline."""
    normalized_query = normalize_query(query)
    clean_query, filters = extract_query_and_filters(normalized_query)

    if metadata_filters:
        filters.update(metadata_filters)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    return rerank(clean_query, results, top_n)
