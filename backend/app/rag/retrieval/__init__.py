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
    from .extractor import extract_query_and_filters
    from .filters import build_qdrant_filter
    from .normalizer import normalize_user_query as normalize_query
    from .prompt import answer_question, stream_answer_question, stream_llm_response
    from .rerank import normalize_scores, rerank
    from .semantic import semantic_search
    from .service import hybrid_search, search, search_with_details
    from .session_manager import SessionChatManager, session_manager

_EXPORTS = {
    "answer_question": (".prompt", "answer_question"),
    "stream_answer_question": (".prompt", "stream_answer_question"),
    "stream_llm_response": (".prompt", "stream_llm_response"),
    "build_qdrant_filter": (".filters", "build_qdrant_filter"),
    "extract_query_and_filters": (".extractor", "extract_query_and_filters"),
    "hybrid_search": (".service", "hybrid_search"),
    "normalize_query": (".normalizer", "normalize_user_query"),
    "normalize_scores": (".rerank", "normalize_scores"),
    "rerank": (".rerank", "rerank"),
    "search": (".service", "search"),
    "search_with_details": (".service", "search_with_details"),
    "semantic_search": (".semantic", "semantic_search"),
    "session_manager": (".session_manager", "session_manager"),
    "SessionChatManager": (".session_manager", "SessionChatManager"),
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
    "stream_answer_question",
    "stream_llm_response",
    "build_qdrant_filter",
    "client",
    "extract_query_and_filters",
    "get_embed_model",
    "get_reranker",
    "hybrid_search",
    "normalize_query",
    "normalize_scores",
    "rerank",
    "search",
    "search_with_details",
    "semantic_search",
    "session_manager",
    "SessionChatManager",
)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
