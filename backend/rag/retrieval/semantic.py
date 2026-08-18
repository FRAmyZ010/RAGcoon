from qdrant_client.http.exceptions import ResponseHandlingException

from .config import COLLECTION_NAME, client, get_embed_model
from .filters import build_qdrant_filter


def semantic_search(
    query: str,
    top_k: int,
    metadata_filters: dict | None = None,
) -> list[dict]:
    query_vector = get_embed_model().embed_query(f"query: {query}")
    query_filter = build_qdrant_filter(metadata_filters)

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
        )
    except (ResponseHandlingException, ValueError, TypeError, RuntimeError):
        return []

    return [
        {
            "text": point.payload["content"],
            "score": point.score,
            # Keep the filename saved during ingestion.  The previous code
            # overwrote every result with one hard-coded filename.
            "payload": {
                **point.payload,
                "source": point.payload.get("source", "Unknown source"),
            },
        }
        for point in results.points
        if point.payload and point.payload.get("content")
    ]
