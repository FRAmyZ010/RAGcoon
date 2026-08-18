import time

from .config import DEFAULT_TOP_K, DEFAULT_TOP_N
from .extractor import QueryFilterProcessor
from .filters import build_qdrant_filter
from .normalizer import normalize_user_query as normalize_query
from .rerank import rerank
from .semantic import semantic_search


def search(query: str) -> list[str]:
    print("\n" + "=" * 60)
    print("ORIGINAL QUERY:", query)

    normalized_query = normalize_query(query)
    print("NORMALIZED QUERY:", normalized_query)

    processor = QueryFilterProcessor(normalized_query)
    clean_query, filters = processor.parse()

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
        print("NORMALIZED QUERY:", normalized_query)
        
        processor = QueryFilterProcessor(normalized_query)
        clean_query, filters = processor.parse()
        print("CLEAN QUERY:", clean_query)
        print("FILTERS:", filters)

        retrieval_start = time.perf_counter()
        results = semantic_search(clean_query, DEFAULT_TOP_K, metadata_filters=filters)
        retrieval_seconds = time.perf_counter() - retrieval_start
        print(f"Retrieved (before rerank): {len(results)} results")
        
        # Debug: show all retrieved chunks with their advisors
        print("\nDEBUG Retrieved chunks:")
        for i, result in enumerate(results[:10], 1):
            advisor = result.get("payload", {}).get("advisor", "N/A")
            text_preview = result["text"].replace("\n", " ")[:60]
            print(f"  {i:2d}. Advisor: {advisor} | {text_preview}")
        
        # Show advisor info from first result
        if results:
            first_advisor = results[0]["payload"].get("advisor", "N/A")
            print(f"\nFirst result advisor: {first_advisor}")

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

        try:
            rerank_start = time.perf_counter()
            reranked = rerank(clean_query, results, DEFAULT_TOP_N)
            rerank_seconds = time.perf_counter() - rerank_start
            print(f"\nAfter rerank: top {len(reranked)} results")
            print("  Reranked chunks:")
            for i, result in enumerate(reranked, 1):
                preview = result["text"].replace("\n", " ")[:70]
                print(f"    [{i}] {preview}...")
        except (TypeError, ValueError, RuntimeError, AttributeError) as e:
            print(f"Error during reranking: {e}")
            rerank_seconds = 0.0
            reranked = results[:DEFAULT_TOP_N]  # Fallback to top semantic results

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
    except (TypeError, ValueError, RuntimeError, AttributeError) as exc:
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
    metadata_filters: dict | None = None,
) -> list[dict]:
    """Compatibility wrapper for the current semantic-search plus rerank pipeline."""
    normalized_query = normalize_query(query)
    processor = QueryFilterProcessor(normalized_query)
    clean_query, filters = processor.parse()

    if metadata_filters:
        filters.update(metadata_filters)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    return rerank(clean_query, results, top_n)
