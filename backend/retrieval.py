from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder
import os

# ================== SETUP ==================
load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

COLLECTION_NAME = "project_documents"


# ================== RETRIEVAL ==================
def retrieve(query: str, top_k: int = 10):
    query_text = f"query: {query}"
    
    query_vector = embed_model.encode(
        [query_text],
        normalize_embeddings=True
    )[0]

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True
    )

    docs = [
        point.payload["text"]
        for point in results.points
        if point.payload and point.payload.get("text")
    ]

    return docs


# ================== RERANK ==================
def rerank(query: str, docs: list[str], top_n: int = 3):
    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in ranked[:top_n]]


# ================== MAIN PIPELINE ==================
def search(query: str):
    docs = retrieve(query)

    # fallback
    if not docs:
        print("⚠️ fallback search...")
        docs = retrieve("pet feeder system design methodology")

    if not docs:
        return []

    return rerank(query, docs)


# ================== RUN ==================
if __name__ == "__main__":
    query = "Methodology of the Petfeeder project"

    results = search(query)

    for i, doc in enumerate(results, 1):
        print(f"\n--- Result {i} ---\n{doc[:500]}...")
