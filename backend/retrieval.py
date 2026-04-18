import os
import time

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from sentence_transformers import CrossEncoder, SentenceTransformer

from performance import format_performance_summary

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
    check_compatibility=False,
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "12"))
DEFAULT_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

embed_model = SentenceTransformer(EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

COLLECTION_NAME = "project_documents" # ชื่อ collection ใน Qdrant ที่เก็บเอกสารของโปรเจค
SAMPLE_QUERIES = [
    "methology of petfeeder",
    "objective of petfeeder",
    "scope of petfeeder",
    "technologies used in petfeeder",
    "how does the petfeeder system work",
]


def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    replacements = {
        "methology": "methodology",
        "methodolgy": "methodology",
        "petfeeder": "pet feeder",
    }

    lowered = normalized.lower()
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)

    return lowered


def build_query_variants(query: str) -> list[str]:
    normalized = normalize_query(query)
    variants: list[str] = [normalized]

    if "methodology" in normalized:
        variants.append(f"{normalized} development process")
        variants.append(f"{normalized} implementation steps")

    if "pet feeder" in normalized:
        variants.append(normalized.replace("pet feeder", "automatic pet feeder"))

    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        if variant and variant not in seen:
            seen.add(variant)
            deduped.append(variant)

    return deduped


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[str]:
    query_text = f"query: {query}"
    query_vector = embed_model.encode([query_text], normalize_embeddings=True)[0]

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
    except ResponseHandlingException as exc:
        raise RuntimeError(f"Qdrant request timed out or failed for query '{query}': {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Qdrant request failed for query '{query}': {exc}") from exc

    return [
        point.payload["text"]
        for point in results.points
        if point.payload and point.payload.get("text")
    ]


def rerank(query: str, docs: list[str], top_n: int = DEFAULT_TOP_N) -> list[dict[str, float | str]]:
    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)
    return [
        {"text": doc, "score": float(score)}
        for doc, score in ranked[:top_n]
    ]


def search_with_details(query: str) -> dict[str, object]:
    total_start = time.perf_counter()
    normalized_query = normalize_query(query)
    query_variants = build_query_variants(query)
    errors: list[str] = []

    retrieval_start = time.perf_counter()
    docs: list[str] = []
    seen: set[str] = set()

    for variant in query_variants:
        try:
            variant_docs = retrieve(variant)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue

        for doc in variant_docs:
            if doc not in seen:
                seen.add(doc)
                docs.append(doc)

    retrieval_seconds = time.perf_counter() - retrieval_start

    rerank_start = time.perf_counter()
    ranked_results = rerank(normalized_query, docs) if docs else []
    rerank_seconds = time.perf_counter() - rerank_start

    total_seconds = time.perf_counter() - total_start

    return {
        "query": query,
        "normalized_query": normalized_query,
        "query_variants": query_variants,
        "retrieved_count": len(docs),
        "results": ranked_results,
        "errors": errors,
        "timing": {
            "retrieval_seconds": retrieval_seconds,
            "rerank_seconds": rerank_seconds,
            "total_seconds": total_seconds,
        },
    }


def search(query: str) -> list[str]:
    details = search_with_details(query)
    return [item["text"] for item in details["results"]]


def format_result_preview(text: str, limit: int = 220) -> str:
    preview = " ".join(text.split())
    if len(preview) <= limit:
        return preview
    return f"{preview[:limit].rstrip()}..."


def run_sample_queries(queries: list[str]) -> None:
    query_times: list[float] = []

    for index, query in enumerate(queries, 1):
        details = search_with_details(query)
        timing = details["timing"]
        results = details["results"]
        query_times.append(timing["total_seconds"])

        print(f"\n===== Query {index} =====")
        print(f"Input query: {details['query']}")
        print(f"Normalized query: {details['normalized_query']}")
        print("Query variants:")
        for variant in details["query_variants"]:
            print(f"- {variant}")

        print(f"Documents before rerank: {details['retrieved_count']}")
        if details["errors"]:
            print("Warnings:")
            for error in details["errors"]:
                print(f"- {error}")
        print("Top results:")
        if not results:
            print("- No results")
        else:
            for rank, item in enumerate(results, 1):
                print(
                    f"[{rank}] score={item['score']:.4f} | "
                    f"{format_result_preview(item['text'])}"
                )

        print(f"Retrieval time: {timing['retrieval_seconds']:.3f}s")
        print(f"Rerank time: {timing['rerank_seconds']:.3f}s")
        print(f"Total time: {timing['total_seconds']:.3f}s")

    print()
    print(format_performance_summary("Queries processed", query_times))


if __name__ == "__main__":
    run_sample_queries(SAMPLE_QUERIES)
