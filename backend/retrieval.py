import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder, SentenceTransformer

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "12"))
DEFAULT_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

embed_model = SentenceTransformer(EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

COLLECTION_NAME = "project_documents"


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

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    return [
        point.payload["text"]
        for point in results.points
        if point.payload and point.payload.get("text")
    ]


def rerank(query: str, docs: list[str], top_n: int = DEFAULT_TOP_N) -> list[str]:
    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)
    return [doc for doc, _ in ranked[:top_n]]


def search(query: str) -> list[str]:
    docs: list[str] = []
    seen: set[str] = set()

    for variant in build_query_variants(query):
        for doc in retrieve(variant):
            if doc not in seen:
                seen.add(doc)
                docs.append(doc)

    if not docs:
        return []

    return rerank(normalize_query(query), docs)


if __name__ == "__main__":
    query = "Methodology of the Petfeeder project"
    results = search(query)

    for i, doc in enumerate(results, 1):
        print(f"\n--- Result {i} ---\n{doc[:500]}...")
