import logging
import os
import threading
import time
import requests

logger = logging.getLogger(__name__)


def prewarm_rag_components() -> None:
    """
    Pre-warm Embedding model, Cross-Encoder reranker, BM25 index, and metadata cache.
    Eliminates the 20+ second Cold Start Penalty on the first user query.
    """
    t0 = time.perf_counter()
    print("🔥 [PRE-WARM] Initializing RAG pipeline components in background...")

    try:
        from .metadata_cache import metadata_cache
        metadata_cache.load_metadata()
        print(f"✅ [PRE-WARM] Metadata Cache loaded ({len(metadata_cache.titles)} titles, {len(metadata_cache.advisors)} advisors).")
    except Exception as e:
        print(f"⚠️ [PRE-WARM] Metadata Cache pre-warm skipped: {e}")

    try:
        from .config import get_embed_model, get_reranker
        get_embed_model()
        print("✅ [PRE-WARM] Dense Multilingual-E5 Embedding model loaded into RAM.")
        get_reranker()
        print("✅ [PRE-WARM] Cross-Encoder Reranker model loaded into RAM.")
    except Exception as e:
        print(f"⚠️ [PRE-WARM] Neural models pre-warm skipped: {e}")

    try:
        from .bm25 import bm25_engine
        bm25_engine.load_index()
        print("✅ [PRE-WARM] In-Memory BM25 Index built and synchronized.")
    except Exception as e:
        print(f"⚠️ [PRE-WARM] BM25 pre-warm skipped: {e}")

    try:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
        requests.post(
            f"{ollama_url.rstrip('/')}/api/generate",
            json={
                "model": ollama_model,
                "keep_alive": "30m",
            },
            timeout=30,
        )
        print(f"✅ [PRE-WARM] Ollama LLM ({ollama_model}) loaded into memory with keep_alive.")
    except Exception as e:
        print(f"⚠️ [PRE-WARM] Ollama pre-warm ping skipped: {e}")

    elapsed = time.perf_counter() - t0
    print(f"🎉 [PRE-WARM] Complete! System is fully warm and primed for instant queries in {elapsed:.2f}s.")


def start_background_prewarm() -> None:
    """Launch pre-warming asynchronously in a background daemon thread."""
    thread = threading.Thread(target=prewarm_rag_components, daemon=True, name="rag-prewarm-thread")
    thread.start()
