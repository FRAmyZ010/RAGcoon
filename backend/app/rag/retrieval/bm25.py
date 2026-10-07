"""
Module: bm25.py
Description:
    High-performance in-memory BM25 (Best Matching 25) search engine for RAGcoon.
    - Synchronizes text chunks and metadata from Qdrant collection into memory.
    - Specialized technical tokenizer preserving code, SQL, hardware model numbers,
      course IDs, hyphenated tokens, and Thai/English terms.
    - Fast filtering and ranked scoring using BM25Okapi.
"""

import logging
import re
import threading
import time
from typing import Any, Optional

import math

class PurePythonBM25Okapi:
    """Pure-Python implementation of BM25Okapi to guarantee zero external dependency failure."""
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25):
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        self.corpus_size = len(corpus)
        self.avgdl = (sum(len(x) for x in corpus) / self.corpus_size) if self.corpus_size > 0 else 1.0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = [len(x) for x in corpus]
        nd = {}
        for document in corpus:
            frequencies = {}
            for word in document:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                nd[word] = nd.get(word, 0) + 1

        idf_sum = 0.0
        negative_idfs = []
        for word, freq in nd.items():
            idf = math.log(self.corpus_size - freq + 0.5) - math.log(freq + 0.5)
            self.idf[word] = idf
            idf_sum += idf
            if idf < 0:
                negative_idfs.append(word)
        self.average_idf = (idf_sum / len(self.idf)) if self.idf else 0.0
        eps = self.epsilon * self.average_idf
        for word in negative_idfs:
            self.idf[word] = eps

    def get_scores(self, query: list[str]) -> list[float]:
        score = [0.0] * self.corpus_size
        doc_len = self.doc_len
        avgdl = self.avgdl
        k1 = self.k1
        b = self.b
        for q in query:
            idf = self.idf.get(q, 0.0)
            if idf <= 0.0:
                continue
            for i, doc in enumerate(self.doc_freqs):
                freq = doc.get(q, 0)
                if freq > 0:
                    numerator = idf * freq * (k1 + 1)
                    denominator = freq + k1 * (1 - b + b * doc_len[i] / avgdl)
                    score[i] += numerator / denominator
        return score

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = PurePythonBM25Okapi

from .config import COLLECTION_NAME, client

logger = logging.getLogger(__name__)


def tokenize_technical_text(text: str) -> list[str]:
    """
    Specialized Tokenizer for Academic, Technical, and Code documents:
    - Preserves hyphenated hardware models (e.g. ESP32-WROOM-32D, STM32F407, BLE-4.0).
    - Preserves course codes & project IDs (e.g. CPE491-2565, CE-PJ-08).
    - Preserves database tables & SQL tokens (e.g. tbl_rfid, tbl_discharge, SELECT, WHERE).
    - Preserves dotted extensions and versions (e.g. Node.js, Final(8).pdf, v2.0).
    - Extracts alphanumeric words and Thai character clusters.
    """
    if not text:
        return []

    # Lowercase while preserving original characters
    norm_text = text.lower()

    # Match technical tokens (hyphenated, underscored, dotted, alphanumeric, Thai)
    pattern = r"[a-zA-Z0-9_\-\.\:\/]+|[\u0e00-\u0e7f]+"
    tokens = re.findall(pattern, norm_text)

    # Clean punctuation edges but keep meaningful inner hyphens/dots
    cleaned_tokens: list[str] = []
    for token in tokens:
        t = token.strip(" .:,;()[]{}'\"")
        if len(t) >= 1:
            cleaned_tokens.append(t)
            # Also break hyphenated tokens into sub-tokens to allow partial matching
            if "-" in t and len(t) > 3:
                for sub_t in t.split("-"):
                    sub_t_clean = sub_t.strip()
                    if len(sub_t_clean) >= 2:
                        cleaned_tokens.append(sub_t_clean)

    return cleaned_tokens


class BM25SearchEngine:
    """In-memory BM25 index cached from Qdrant collection points."""

    def __init__(self, collection_name: str = COLLECTION_NAME, cache_ttl_seconds: int = 3600):
        self.collection_name = collection_name
        self.cache_ttl_seconds = cache_ttl_seconds
        self._lock = threading.Lock()
        self._corpus_docs: list[dict[str, Any]] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._last_loaded_time: float = 0.0
        self._points_count: int = 0

    def load_index(self, force_reload: bool = False) -> None:
        """Fetch all points and payloads from Qdrant and build the BM25 index."""
        with self._lock:
            now = time.time()
            if (
                not force_reload
                and self._bm25 is not None
                and (now - self._last_loaded_time < self.cache_ttl_seconds)
            ):
                return

            try:
                logger.info(f"🔄 Building in-memory BM25 index from Qdrant collection: {self.collection_name}...")
                points_count = client.count(collection_name=self.collection_name).count
                if points_count == 0:
                    logger.warning(f"Collection {self.collection_name} is empty.")
                    self._bm25 = None
                    return

                # Scroll through all points in collection
                all_points = []
                next_offset = None
                while True:
                    records, next_offset = client.scroll(
                        collection_name=self.collection_name,
                        limit=500,
                        offset=next_offset,
                        with_payload=True,
                        with_vectors=False,
                    )
                    all_points.extend(records)
                    if next_offset is None or not records:
                        break

                corpus_docs = []
                tokenized_corpus = []

                for pt in all_points:
                    payload = pt.payload or {}
                    text_content = payload.get("content", "")
                    if not text_content:
                        continue

                    # Enrich indexed text with metadata (title, author, advisor, keywords, source)
                    title = payload.get("project_title") or payload.get("title") or ""
                    author = payload.get("author") or ""
                    advisor = payload.get("advisor") or ""
                    source = payload.get("source") or ""
                    keywords = payload.get("keywords") or ""

                    enriched_text = f"{title} {author} {advisor} {source} {keywords}\n{text_content}"
                    tokens = tokenize_technical_text(enriched_text)

                    corpus_docs.append({
                        "id": pt.id,
                        "text": text_content,
                        "payload": payload,
                    })
                    tokenized_corpus.append(tokens)

                if tokenized_corpus:
                    self._bm25 = BM25Okapi(tokenized_corpus)
                    self._corpus_docs = corpus_docs
                    self._tokenized_corpus = tokenized_corpus
                    self._last_loaded_time = now
                    self._points_count = len(corpus_docs)
                    logger.info(f"✅ BM25 Index successfully built with {len(corpus_docs)} documents.")
                else:
                    self._bm25 = None

            except Exception as e:
                logger.error(f"❌ Failed to load BM25 index from Qdrant: {e}", exc_info=True)

    def search(
        self,
        query: str,
        top_k: int = 25,
        metadata_filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform BM25 Keyword Search with optional metadata filtering.
        
        Returns:
            list of dict: [{"text": ..., "score": bm25_score, "payload": {...}}]
        """
        if not self._bm25 or not self._corpus_docs:
            self.load_index()

        if not self._bm25 or not self._corpus_docs:
            return []

        query_tokens = tokenize_technical_text(query)
        if not query_tokens:
            return []

        # Calculate BM25 scores across all corpus documents
        scores = self._bm25.get_scores(query_tokens)

        # Filter by metadata if specified
        results = []
        for idx, score in enumerate(scores):
            if score <= 0.0:
                continue

            doc = self._corpus_docs[idx]
            payload = doc["payload"]

            if metadata_filters:
                from .metadata_cache import metadata_cache
                match = True
                for k, v in metadata_filters.items():
                    if k in ("compared_projects", "target_domains") or v is None or v == "" or v == []:
                        continue

                    if k == "advisor":
                        target_advisors = v if isinstance(v, list) else [v]
                        all_allowed = set()
                        for adv in target_advisors:
                            adv_str = str(adv).strip()
                            if not adv_str:
                                continue
                            resolved = metadata_cache.resolve_advisor_variants(adv_str)
                            if resolved:
                                all_allowed.update(resolved)
                            else:
                                all_allowed.add(adv_str)

                        p_adv = str(payload.get("advisor", "")).strip()
                        adv_match = (
                            p_adv in all_allowed
                            or any(al.lower() in p_adv.lower() or p_adv.lower() in al.lower() for al in all_allowed)
                        )
                        if not adv_match:
                            match = False
                            break

                    elif k == "author":
                        target_authors = v if isinstance(v, list) else [v]
                        all_allowed_auth = set()
                        for auth in target_authors:
                            auth_str = str(auth).strip()
                            if not auth_str:
                                continue
                            resolved = metadata_cache.resolve_author_variants(auth_str)
                            if resolved:
                                all_allowed_auth.update(resolved)
                            else:
                                all_allowed_auth.add(auth_str)

                        p_auth = str(payload.get("author", "")).strip()
                        auth_match = (
                            p_auth in all_allowed_auth
                            or any(al.lower() in p_auth.lower() or p_auth.lower() in al.lower() for al in all_allowed_auth)
                        )
                        if not auth_match:
                            match = False
                            break

                    elif k == "year":
                        p_year = str(payload.get("year", "")).strip()
                        if str(v).strip() != p_year:
                            match = False
                            break

                    elif k in ("project_title", "title"):
                        p_title = str(payload.get("project_title") or payload.get("title") or "").lower().strip()
                        v_title = str(v).lower().strip()
                        if v_title not in p_title and p_title not in v_title:
                            match = False
                            break

                if not match:
                    continue

            results.append({
                "text": doc["text"],
                "score": float(score),
                "payload": {
                    **payload,
                    "source": payload.get("source", "Unknown source"),
                },
            })

        # Sort descending by BM25 score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# Global singleton instance of BM25 Engine
bm25_engine = BM25SearchEngine()
