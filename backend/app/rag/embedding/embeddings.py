"""Shared embedding loader for ingest + retrieval."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

# Force CPU before torch allocates CUDA contexts inside the container.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


class CpuSentenceEmbeddings:
    """Minimal embeddings API compatible with our Qdrant/RAG call sites."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        # low_cpu_mem_usage=False avoids transformers loading weights onto the
        # meta device, which later crashes encode() with:
        # "Cannot copy out of meta tensor".
        self._model = SentenceTransformer(
            model_name,
            device="cpu",
            model_kwargs={"low_cpu_mem_usage": False},
        )

    def _prefix_documents(self, texts: List[str]) -> List[str]:
        # multilingual-e5 expects passage:/query: prefixes for best quality.
        if "e5" not in self.model_name.lower():
            return texts
        out: List[str] = []
        for text in texts:
            raw = text or ""
            if raw.startswith("passage:") or raw.startswith("query:"):
                out.append(raw)
            else:
                out.append(f"passage: {raw}")
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            self._prefix_documents(list(texts)),
            normalize_embeddings=True,
            batch_size=4,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        raw = text or ""
        if "e5" in self.model_name.lower() and not (
            raw.startswith("query:") or raw.startswith("passage:")
        ):
            raw = f"query: {raw}"
        vector = self._model.encode(
            [raw],
            normalize_embeddings=True,
            batch_size=1,
            show_progress_bar=False,
        )[0]
        return vector.tolist()


@lru_cache(maxsize=1)
def get_shared_embedding_model(model_name: str) -> CpuSentenceEmbeddings:
    return CpuSentenceEmbeddings(model_name)
