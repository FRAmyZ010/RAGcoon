import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

load_dotenv(find_dotenv())

QDRANT_URL: str | None = os.getenv("QDRANT_URL")
QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL is not set")

if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY is not set")

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "embedding_evaluation")

DEFAULT_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "20"))
DEFAULT_TOP_N: int = int(os.getenv("RERANK_TOP_N", "5"))

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
