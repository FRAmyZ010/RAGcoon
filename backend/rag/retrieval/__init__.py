"""Public retrieval API with deferred imports.

Utilities can now be imported without opening Qdrant or loading ML models.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import (
        COLLECTION_NAME,
        DEFAULT_TOP_K,
        DEFAULT_TOP_N,
        EMBEDDING_MODEL,
        QDRANT_API_KEY,
        QDRANT_URL,
        client,
        get_embed_model,
        get_reranker,
    )
    from .debug import run_sample_queries
    from .extractor import extract_query_and_filters
    from .filters import build_qdrant_filter
    from .normalizer import normalize_user_query as normalize_query
    from .performance import format_performance_summary
    from .prompt import answer_question
    from .rerank import normalize_scores, rerank
    from .semantic import semantic_search
    from .service import hybrid_search, search, search_with_details

_EXPORTS = {
    "answer_question": (".prompt", "answer_question"),
    "build_qdrant_filter": (".filters", "build_qdrant_filter"),
    "extract_query_and_filters": (".extractor", "extract_query_and_filters"),
    "format_performance_summary": (".performance", "format_performance_summary"),
    "hybrid_search": (".service", "hybrid_search"),
    "normalize_query": (".normalizer", "normalize_user_query"),
    "normalize_scores": (".rerank", "normalize_scores"),
    "rerank": (".rerank", "rerank"),
    "run_sample_queries": (".debug", "run_sample_queries"),
    "search": (".service", "search"),
    "search_with_details": (".service", "search_with_details"),
    "semantic_search": (".semantic", "semantic_search"),
    "COLLECTION_NAME": (".config", "COLLECTION_NAME"),
    "DEFAULT_TOP_K": (".config", "DEFAULT_TOP_K"),
    "DEFAULT_TOP_N": (".config", "DEFAULT_TOP_N"),
    "EMBEDDING_MODEL": (".config", "EMBEDDING_MODEL"),
    "QDRANT_API_KEY": (".config", "QDRANT_API_KEY"),
    "QDRANT_URL": (".config", "QDRANT_URL"),
    "client": (".config", "client"),
    "get_embed_model": (".config", "get_embed_model"),
    "get_reranker": (".config", "get_reranker"),
}

__all__ = (
    "COLLECTION_NAME",
    "DEFAULT_TOP_K",
    "DEFAULT_TOP_N",
    "EMBEDDING_MODEL",
    "QDRANT_API_KEY",
    "QDRANT_URL",
    "answer_question",
    "build_qdrant_filter",
    "client",
    "extract_query_and_filters",
    "format_performance_summary",
    "get_embed_model",
    "get_reranker",
    "hybrid_search",
    "normalize_query",
    "normalize_scores",
    "rerank",
    "run_sample_queries",
    "search",
    "search_with_details",
    "semantic_search",
)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
