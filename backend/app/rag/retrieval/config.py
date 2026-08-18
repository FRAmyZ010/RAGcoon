import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder


load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL:
    raise ValueError("QDRANT_URL is not set")

if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY is not set")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "embedding_evaluation")

DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))
DEFAULT_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
    check_compatibility=False,
)

embed_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
