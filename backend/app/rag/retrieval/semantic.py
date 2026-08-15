from typing import Dict, List, Optional

from qdrant_client.http.exceptions import ResponseHandlingException

from .config import COLLECTION_NAME, client, embed_model
from .filters import build_qdrant_filter


DEFAULT_SOURCE = "QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"


def semantic_search(
    query: str,
    top_k: int,
    metadata_filters: Optional[Dict] = None,
) -> List[Dict]:
    query_vector = embed_model.embed_query(f"query: {query}")
    query_filter = build_qdrant_filter(metadata_filters)

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
        )
    except ResponseHandlingException:
        return []
    except Exception:
        return []

    return [
        {
            "text": point.payload["content"],
            "score": point.score,
            "payload": {**point.payload, "source": DEFAULT_SOURCE},
        }
        for point in results.points
        if point.payload and point.payload.get("content")
    ]
