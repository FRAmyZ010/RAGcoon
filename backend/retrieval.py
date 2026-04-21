import os 
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from sentence_transformers import CrossEncoder
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from performance import format_performance_summary

# =========================
# ENV & INIT
# =========================
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL is not set")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
    check_compatibility=False,
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "embedding_experiment")

DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "12"))
DEFAULT_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

embed_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# =========================
# QUERY UTILS
# =========================
def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())

    replacements = {
        "methology": "methodology",
        "methodolgy": "methodology",
        "petfeeder": "pet feeder",
    }

    lowered = normalized.lower()
    for src, tgt in replacements.items():
        lowered = lowered.replace(src, tgt)

    return lowered


def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return scores

    min_s, max_s = min(scores), max(scores)

    if max_s == min_s:
        return [0.5] * len(scores)

    return [(s - min_s) / (max_s - min_s) for s in scores]


# =========================
# FILTER
# =========================
def build_qdrant_filter(filters: Optional[Dict]) -> Optional[Filter]:
    if not filters:
        return None

    conditions = []

    for key, value in filters.items():
        if isinstance(value, list):
            conditions.append(
                FieldCondition(key=key, match=MatchAny(any=value))
            )
        else:
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )

    return Filter(must=conditions)


# =========================
# SEARCH CORE
# =========================
def keyword_search_qdrant(query: str, top_k: int) -> List[Dict]:
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query,
            limit=top_k,
            with_payload=True,
        )
    except Exception:
        return []

    return [
        {"text": p.payload.get("content", ""), "score": p.score}
        for p in results.points
        if p.payload and p.payload.get("content")
    ]


def semantic_search(query: str, top_k: int, metadata_filters=None) -> List[Dict]:
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
        {"text": p.payload["content"], "score": p.score}
        for p in results.points
        if p.payload and p.payload.get("content")
    ]


# =========================
# RERANK
# =========================
def rerank(query: str, docs: List[str], top_n: int) -> List[Dict]:
    if not docs:
        return []

    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    top_docs = ranked[:top_n]
    norm_scores = normalize_scores([s for _, s in top_docs])

    return [
        {"text": doc, "score": float(norm)}
        for (doc, _), norm in zip(top_docs, norm_scores)
    ]


# =========================
# HYBRID SEARCH (FIXED)
# =========================
def hybrid_search(
    query: str,
    metadata_filters=None,
    top_k: int = DEFAULT_TOP_K,
    top_n: int = DEFAULT_TOP_N,
) -> List[Dict]:

    query = normalize_query(query)

    semantic = semantic_search(query, top_k, metadata_filters)
    keyword = keyword_search_qdrant(query, top_k)

    if not semantic and not keyword:
        return []

    # normalize
    sem_scores = normalize_scores([r["score"] for r in semantic])
    key_scores = normalize_scores([r["score"] for r in keyword])

    sem_map = {r["text"]: sem_scores[i] for i, r in enumerate(semantic)}
    key_map = {r["text"]: key_scores[i] for i, r in enumerate(keyword)}

    combined = {}

    # merge
    for doc, score in sem_map.items():
        combined[doc] = score * 0.6

    for doc, score in key_map.items():
        combined[doc] = combined.get(doc, 0) + score * 0.4

    # 👉 FIX สำคัญ: sort ก่อน normalize
    combined_items = sorted(
        combined.items(),
        key=lambda x: x[1],
        reverse=True
    )

    docs = [doc for doc, _ in combined_items]
    hybrid_scores = normalize_scores([score for _, score in combined_items])

    hybrid_map = dict(zip(docs, hybrid_scores))

    reranked = rerank(query, docs, top_n)

    # blend score
    for r in reranked:
        r["score"] = r["score"] * 0.7 + hybrid_map.get(r["text"], 0) * 0.3

    return reranked


# =========================
# MAIN SEARCH
# =========================
def search(query: str) -> List[str]:
    results = hybrid_search(query)
    return [r["text"] for r in results]


# =========================
# DEBUG / TEST
# =========================
def run_sample_queries(queries: List[str]) -> None:
    times = []

    for q in queries:
        start = time.perf_counter()
        results = hybrid_search(q)
        elapsed = time.perf_counter() - start

        times.append(elapsed)

        print(f"\nQuery: {q}")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['score']:.4f} | {r['text'][:80]}...")

        print(f"Time: {elapsed:.3f}s")

    print("\n" + format_performance_summary("Queries processed", times))


if __name__ == "__main__":
    SAMPLE_QUERIES = [
        "methology of petfeeder",
        "objective of petfeeder",
        "scope of petfeeder",
        "technologies used in petfeeder",
        "how does the petfeeder system work",
    ]

    run_sample_queries(SAMPLE_QUERIES)