"""
Module: hybrid.py
Description:
    True Hybrid Retrieval Engine for RAGcoon.
    - Combines Dense Vector Search (Multilingual-E5) and Sparse Keyword Search (BM25).
    - Merges results using Reciprocal Rank Fusion (RRF).
    - Preserves exact technical identifiers (chipsets, SQL, course codes) while retaining
      deep semantic understanding across Thai & English languages.
"""

import logging
from typing import Any, Optional

from .bm25 import bm25_engine
from .semantic import semantic_search

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    dense_weight: float = 0.5,
    bm25_weight: float = 0.5,
    rrf_k: int = 60,
    top_k: int = 25,
) -> list[dict[str, Any]]:
    """
    Combine Dense Vector and BM25 results using Reciprocal Rank Fusion (RRF).
    
    Formula:
        Score(d) = (dense_weight / (rrf_k + rank_dense(d))) + (bm25_weight / (rrf_k + rank_bm25(d)))
    """
    doc_scores: dict[str, float] = {}
    doc_map: dict[str, dict[str, Any]] = {}
    dense_ranks: dict[str, int] = {}
    bm25_ranks: dict[str, int] = {}
    raw_dense_scores: dict[str, float] = {}
    raw_bm25_scores: dict[str, float] = {}

    def get_doc_key(item: dict[str, Any]) -> str:
        payload = item.get("payload", {}) or {}
        source = str(payload.get("source", ""))
        page = str(payload.get("page_number", ""))
        text_snippet = str(item.get("text", "")).strip()[:150]
        return f"{source}__p{page}__{hash(text_snippet)}"

    # 1. Process Dense Vector Ranks
    for rank, item in enumerate(dense_results, start=1):
        key = get_doc_key(item)
        dense_ranks[key] = rank
        raw_dense_scores[key] = float(item.get("score", 0.0))
        doc_map[key] = item
        score_contrib = dense_weight / (rrf_k + rank)
        doc_scores[key] = doc_scores.get(key, 0.0) + score_contrib

    # 2. Process BM25 Sparse Ranks
    for rank, item in enumerate(bm25_results, start=1):
        key = get_doc_key(item)
        bm25_ranks[key] = rank
        raw_bm25_scores[key] = float(item.get("score", 0.0))
        if key not in doc_map:
            doc_map[key] = item
        score_contrib = bm25_weight / (rrf_k + rank)
        doc_scores[key] = doc_scores.get(key, 0.0) + score_contrib

    # 3. Sort by combined RRF score
    sorted_keys = sorted(doc_scores.keys(), key=lambda k: doc_scores[k], reverse=True)

    max_possible_score = (dense_weight / (rrf_k + 1)) + (bm25_weight / (rrf_k + 1))

    fused_results: list[dict[str, Any]] = []
    for key in sorted_keys[:top_k]:
        item = doc_map[key]
        raw_rrf = doc_scores[key]
        norm_score = raw_rrf / max_possible_score if max_possible_score > 0 else raw_rrf

        fused_item = {
            "text": item.get("text", ""),
            "score": float(norm_score),
            "payload": item.get("payload", {}),
            "retrieval_meta": {
                "rrf_score": float(raw_rrf),
                "dense_rank": dense_ranks.get(key),
                "bm25_rank": bm25_ranks.get(key),
                "dense_raw_score": raw_dense_scores.get(key),
                "bm25_raw_score": raw_bm25_scores.get(key),
            },
        }
        fused_results.append(fused_item)

    return fused_results


def hybrid_search(
    query: str,
    top_k: int = 25,
    metadata_filters: Optional[dict[str, Any]] = None,
    dense_weight: float = 0.5,
    bm25_weight: float = 0.5,
    candidate_pool_size: int = 20,
) -> list[dict[str, Any]]:
    """
    Execute True Hybrid Search (Dense Vector + BM25 Sparse + RRF).
    
    1. Runs Dense Vector Semantic Search in Qdrant.
    2. Runs BM25 Keyword Search in memory index.
    3. Merges and re-ranks candidate pools via Reciprocal Rank Fusion.
    """
    pool_k = max(top_k, candidate_pool_size)

    # 1. Dense Semantic Search
    try:
        dense_results = semantic_search(query, pool_k, metadata_filters=metadata_filters)
    except Exception as exc:
        logger.error(f"Dense vector search failed: {exc}")
        dense_results = []

    # 2. BM25 Keyword Search
    try:
        bm25_results = bm25_engine.search(query, pool_k, metadata_filters=metadata_filters)
    except Exception as exc:
        logger.error(f"BM25 search failed: {exc}")
        bm25_results = []

    # Fallbacks if one engine returns empty
    if dense_results and not bm25_results:
        return dense_results[:top_k]
    if bm25_results and not dense_results:
        return bm25_results[:top_k]
    if not dense_results and not bm25_results:
        return []

    # 3. Fuse via Reciprocal Rank Fusion (RRF)
    return reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        dense_weight=dense_weight,
        bm25_weight=bm25_weight,
        rrf_k=60,
        top_k=top_k,
    )
