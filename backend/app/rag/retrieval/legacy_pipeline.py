"""
Module: legacy_pipeline.py
Description:
    Preserved Legacy Retrieval & Answering Pipeline (Pre-LLM Query Processor / Baseline from commit 8346e21).
    Used for A/B Testing, Sensitivity Analysis, and Academic Benchmark Comparisons against Modern True Hybrid RAG.

Characteristics of Legacy Pipeline:
    1. Query Processing: Rule-based normalizer & regex filter extractor (no LLM in query processor).
    2. Retrieval Engine: Dense Vector Search only (Multilingual-E5, fixed top_k=15, NO BM25, NO RRF).
    3. Re-ranking: Fixed top_n=5 cross-encoder (NO dynamic intent quota, NO boilerplate filtering).
    4. Generation: Generic single prompt (NO intent-specific prompting, NO strict anti-hallucination rules).
    5. No Fast-Path: All metadata queries must go through dense vector search & cross-encoder.
"""

import os
import re
import time
from typing import Any, Optional
import requests

from .config import COLLECTION_NAME, DEFAULT_NUM_CTX, DEFAULT_TOP_K, DEFAULT_TOP_N
from .filters import build_qdrant_filter
from .metadata_cache import metadata_cache
from .rerank import rerank
from .semantic import semantic_search

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


# =========================================================================
# 1. Legacy Rule-based Normalizer & Regex Helpers
# =========================================================================

KV_PATTERN = re.compile(
    r"\b(advisor|author|year|title|keyword)\s*[:=]\s*(?:\"([^\"]+)\"|'([^']+)'|(\S+))",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

ADVISOR_EXACT_MAP = {
    "surapol": "Aj. Surapol Vorapatratorn",
    "pattaramon": "Asst. Prof. Pattaramon Vuttipittayamongkol, Ph. D",
    "nattapol": "Assoc. Prof. Nattapol Aunsri, Ph. D",
    "tossapon": "Assoc. Prof. Wg. Cdr. Dr. Tossapon Boongoen",
    "natthakan": "Asst. Prof. Dr. Natthakan Iam-On",
    "phitsanu": "Asst. Prof. Dr. Phitsanu Phoomvuthisarn",
    "chayapol": "Asst. Prof. Dr. Chayapol Kamyod",
    "teeravisit": "Aj. Dr. Teeravisit Laothanapanich",
    "rawiwan": "Aj. Dr. Rawiwan Wongpromsub",
}

MFU_STAFF = [
    "Surapol Vorapatratorn",
    "Pattaramon Vuttipittayamongkol",
    "Nattapol Aunsri",
    "Tossapon Boongoen",
    "Natthakan Iam-On",
    "Phitsanu Phoomvuthisarn",
    "Chayapol Kamyod",
    "Teeravisit Laothanapanich",
    "Rawiwan Wongpromsub",
]


def legacy_normalize_user_query(query: str) -> str:
    """Legacy rule-based query normalization (lowercase, whitespace collapse, simple synonym replacement)."""
    lowered = " ".join(query.strip().split()).lower()
    synonyms = {
        "ce": "computer engineering",
        "cpe": "computer engineering",
        "se": "software engineering",
        "db": "database",
    }
    tokens = lowered.split()
    return " ".join([synonyms.get(t, t) for t in tokens])


class LegacyQueryFilterProcessor:
    """Legacy rule-based filter extractor from user queries."""

    def __init__(self, user_query: str):
        self.user_query = user_query

    def extract_filters(self) -> tuple[str, dict[str, Any]]:
        filters: dict[str, Any] = {}
        clean_query = self.user_query

        # Key-Value syntax (e.g. advisor:surapol)
        for match in KV_PATTERN.finditer(self.user_query):
            key = match.group(1).lower()
            if key == "title":
                key = "project_title"
            val = match.group(2) or match.group(3) or match.group(4)
            if val:
                filters[key] = val.strip()
                clean_query = clean_query.replace(match.group(0), "")

        # 4-digit Year
        year_match = YEAR_PATTERN.search(clean_query)
        if year_match:
            filters["year"] = year_match.group()
            clean_query = YEAR_PATTERN.sub("", clean_query)

        # In-memory dictionary matching
        if not filters.get("advisor"):
            lower_clean = clean_query.lower()
            for short_name, exact_name in ADVISOR_EXACT_MAP.items():
                if re.search(r"\b" + re.escape(short_name) + r"\b", lower_clean):
                    filters["advisor"] = exact_name
                    clean_query = re.sub(r"\b" + re.escape(short_name) + r"\b", "", clean_query, flags=re.IGNORECASE)
                    break

        if not filters.get("advisor"):
            for staff in MFU_STAFF:
                if re.search(r"\b" + re.escape(staff.lower()) + r"\b", clean_query.lower()):
                    filters["advisor"] = staff
                    clean_query = re.sub(r"\b" + re.escape(staff) + r"\b", "", clean_query, flags=re.IGNORECASE)
                    break

        # Match known titles in metadata cache
        if not filters.get("project_title") and metadata_cache.titles:
            lower_clean = clean_query.lower()
            for title in sorted(metadata_cache.titles, key=len, reverse=True):
                if len(title) >= 5 and title.lower() in lower_clean:
                    filters["project_title"] = title
                    clean_query = re.sub(re.escape(title), "", clean_query, flags=re.IGNORECASE)
                    break

        clean_query = " ".join(clean_query.split()).strip(" ,;:-_")
        return clean_query, filters


# =========================================================================
# 2. Legacy Retrieval Engine (Vector Search Only, Fixed Top-K & Top-N)
# =========================================================================

def legacy_search_with_details(query: str) -> dict[str, Any]:
    """
    Legacy retrieval search:
      - Uses Rule-based Normalizer + Rule-based Filter Extractor
      - Dense Vector Search only (semantic_search, fixed top_k=15)
      - Fixed cross-encoder reranking (top_n=5)
      - NO Fast-Path, NO BM25, NO RRF, NO Boilerplate filtering
    """
    total_start = time.perf_counter()
    normalized_query = legacy_normalize_user_query(query)
    processor = LegacyQueryFilterProcessor(normalized_query)
    clean_query, filters = processor.extract_filters()

    retrieval_start = time.perf_counter()
    try:
        results = semantic_search(clean_query or normalized_query, DEFAULT_TOP_K, metadata_filters=filters)
    except Exception as exc:
        results = []
    retrieval_seconds = time.perf_counter() - retrieval_start

    rerank_seconds = 0.0
    reranked = []
    if results:
        try:
            rerank_start = time.perf_counter()
            reranked = rerank(clean_query or normalized_query, results, DEFAULT_TOP_N)
            rerank_seconds = time.perf_counter() - rerank_start
        except Exception:
            reranked = results[:DEFAULT_TOP_N]

    total_seconds = time.perf_counter() - total_start
    return {
        "pipeline": "legacy",
        "results": reranked,
        "retrieved_count": len(results),
        "normalized_query": normalized_query,
        "clean_query": clean_query,
        "filters": filters,
        "intent": "GENERIC",  # Legacy had no intent classifier
        "fast_path_used": False,
        "timing": {
            "query_proc_seconds": 0.001,  # Sub-millisecond rule-based
            "retrieval_seconds": retrieval_seconds,
            "rerank_seconds": rerank_seconds,
            "total_seconds": total_seconds,
        },
    }


# =========================================================================
# 3. Legacy Generation (Single Generic Prompt, Fixed Token Quota)
# =========================================================================

def legacy_answer_question(query: str) -> dict[str, Any]:
    """
    Legacy RAG generation:
      - Executes legacy_search_with_details
      - Uses legacy generic single prompt
      - Fixed num_predict=512, temperature=0
      - NO intent-specific routing, NO boilerplate cleanup
    """
    t0 = time.perf_counter()
    retrieval_details = legacy_search_with_details(query)
    scored_contexts = retrieval_details.get("results", [])

    is_thai = any("\u0e00" <= c <= "\u0e7f" for c in query)
    context_list = []
    sources = []

    for item in scored_contexts:
        p = item.get("payload", {}) or {}
        src = p.get("source", "Unknown")
        page = p.get("page_number", "?")
        title = p.get("project_title") or p.get("title", "")
        author = p.get("author", "")
        advisor = p.get("advisor", "")
        txt = item.get("text", "")

        header = f"Project title: {title} | Author: {author} | Advisor: {advisor} | Source: {src} (Page {page})"
        context_list.append(f"{header}\n{txt}")
        if src not in sources:
            sources.append(src)

    context_text = "\n\n".join(context_list)
    lang_instruction = "Please respond in Thai language directly and concisely." if is_thai else "Please respond in English directly and concisely."
    insufficient_reply = "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร" if is_thai else "I don't know."

    legacy_prompt = f"""You are an assistant for a senior project document repository.
Use only the retrieved context below. Do not invent facts.

Instructions:
1. Check both the metadata headers and the document content thoroughly.
2. If the question asks for tools, frameworks, hardware, sensors, technologies, extract and summarize all relevant items.
3. {lang_instruction}
4. Only if the context contains absolutely no relevant information, reply exactly: {insufficient_reply}
5. Keep the answer concise and directly relevant to the question.

Context:
{context_text}

Question:
{query}

Answer:
"""

    llm_start = time.perf_counter()
    answer_text = ""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": legacy_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 512,
                },
            },
            timeout=120,
        )
        if resp.status_code == 200:
            answer_text = resp.json().get("response", "").strip()
        else:
            answer_text = f"LLM error: HTTP {resp.status_code}"
    except Exception as exc:
        answer_text = f"LLM generation failed: {exc}"

    llm_seconds = time.perf_counter() - llm_start
    total_seconds = time.perf_counter() - t0

    return {
        "pipeline": "legacy",
        "query": query,
        "clean_query": retrieval_details.get("clean_query", query),
        "answer": answer_text,
        "filters": retrieval_details.get("filters", {}),
        "sources": sources,
        "scored_contexts": scored_contexts,
        "retrieved_count": retrieval_details.get("retrieved_count", 0),
        "timing": {
            "query_proc_seconds": retrieval_details["timing"].get("query_proc_seconds", 0.001),
            "retrieval_seconds": retrieval_details["timing"]["retrieval_seconds"],
            "rerank_seconds": retrieval_details["timing"]["rerank_seconds"],
            "llm_seconds": llm_seconds,
            "total_seconds": total_seconds,
        },
    }
