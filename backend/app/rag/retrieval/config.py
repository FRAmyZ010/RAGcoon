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

DEFAULT_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "15"))
DEFAULT_TOP_N: int = int(os.getenv("RERANK_TOP_N", "5"))
DEFAULT_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

INTENT_CONFIG: dict[str, dict[str, Any]] = {
    "FACTUAL_LOOKUP": {
        "top_k": 15,
        "rerank_top_n": 5,
        "num_predict": 512,
        "max_context_chunks": 5,
        "thinking": False,
    },
    "FACTOID": {
        "top_k": 15,
        "rerank_top_n": 5,
        "num_predict": 512,
        "max_context_chunks": 5,
        "thinking": False,
    },
    "EXPLANATION": {
        "top_k": 15,
        "rerank_top_n": 5,
        "num_predict": 640,
        "max_context_chunks": 5,
        "thinking": False,
    },
    "DEEP_DIVE": {
        "top_k": 15,
        "rerank_top_n": 5,
        "num_predict": 1024,
        "max_context_chunks": 5,
        "thinking": False,
    },
    "COMPARISON": {
        "top_k": 24,
        "rerank_top_n": 6,
        "num_predict": 768,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "RECOMMENDATION": {
        "top_k": 24,
        "rerank_top_n": 8,
        "num_predict": 768,
        "max_context_chunks": 6,
        "thinking": False,
    },
    "EXPLORATORY": {
        "top_k": 25,
        "rerank_top_n": 12,
        "num_predict": 640,
        "max_context_chunks": 10,
        "thinking": False,
    },
    "CODE": {
        "top_k": 15,
        "rerank_top_n": 5,
        "num_predict": 768,
        "max_context_chunks": 5,
        "thinking": False,
    },
}

client: QdrantClient = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
    check_compatibility=False,
)


import threading

_embed_lock = threading.Lock()
_embed_model: HuggingFaceEmbeddings | None = None

_rerank_lock = threading.Lock()
_reranker: CrossEncoder | None = None


def get_embed_model() -> HuggingFaceEmbeddings:
    """Load the embedding model safely with thread lock to prevent concurrent initialization race conditions."""
    global _embed_model
    if _embed_model is None:
        with _embed_lock:
            if _embed_model is None:
                _embed_model = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embed_model


def get_reranker() -> CrossEncoder:
    """Load the reranker safely with thread lock to prevent concurrent initialization race conditions."""
    global _reranker
    if _reranker is None:
        with _rerank_lock:
            if _reranker is None:
                _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
    return _reranker