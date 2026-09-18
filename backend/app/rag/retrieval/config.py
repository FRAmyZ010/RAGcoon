import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

# Load .env from backend or root directory
env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(find_dotenv(usecwd=True))

QDRANT_URL: str | None = os.getenv("QDRANT_URL")
QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL is not set")

if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY is not set")

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "embedding_evaluation")

DEFAULT_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "25"))
DEFAULT_TOP_N: int = int(os.getenv("RERANK_TOP_N", "7"))

INTENT_CONFIG: dict[str, dict[str, Any]] = {
    "FACTUAL_LOOKUP": {
        "top_k": 25,
        "rerank_top_n": 6,
        "num_predict": 384,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "FACTOID": {
        "top_k": 25,
        "rerank_top_n": 6,
        "num_predict": 384,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "EXPLANATION": {
        "top_k": 20,
        "rerank_top_n": 6,
        "num_predict": 512,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "DEEP_DIVE": {
        "top_k": 20,
        "rerank_top_n": 6,
        "num_predict": 512,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "COMPARISON": {
        "top_k": 40,
        "rerank_top_n": 6,
        "num_predict": 512,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "RECOMMENDATION": {
        "top_k": 60,
        "rerank_top_n": 15,
        "num_predict": 650,
        "max_context_chunks": 8,
        "thinking": False,
    },
    "EXPLORATORY": {
        "top_k": 40,
        "rerank_top_n": 10,
        "num_predict": 512,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "CODE": {
        "top_k": 20,
        "rerank_top_n": 6,
        "num_predict": 512,
        "max_context_chunks": 6,
        "thinking": False,
    },
}

client: QdrantClient = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
    check_compatibility=False,
)


@lru_cache(maxsize=1)
def get_embed_model() -> HuggingFaceEmbeddings:
    """Load the embedding model only for an actual semantic search."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """Load the reranker only when results need reranking."""
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")