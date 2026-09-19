import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from .config import DEFAULT_TOP_K, DEFAULT_TOP_N, INTENT_CONFIG
from .extractor import QueryFilterProcessor
from .filters import build_qdrant_filter
from .normalizer import normalize_user_query as normalize_query
from .rerank import rerank
from .semantic import semantic_search


from .llm_query_processor import process_query_with_llm


def _get_routing_params(intent: str) -> tuple[int, int]:
    """Return adaptive (top_k, top_n) based on query intent from INTENT_CONFIG."""
    cfg = INTENT_CONFIG.get(intent, INTENT_CONFIG.get("FACTOID", {}))
    top_k = cfg.get("top_k", DEFAULT_TOP_K)
    top_n = cfg.get("rerank_top_n", DEFAULT_TOP_N)
    return top_k, top_n


def is_boilerplate_text(text: str) -> bool:
    """
    Check if snippet is mostly table of contents, pure bibliography/references,
    pure acknowledgements, appendix title pages, committee signatures, or bare page numbers.
    Never filters out Technical Sections, Hardware, Methodology, Inputs, or Abstracts.
    """
    if not text or not text.strip():
        return True

    t = text.lower()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1. Bare page number or ultra short non-technical lines
    if len(lines) <= 2 and len(text.strip()) < 50:
        if all(re.match(r"^\d+$|^page\s*\d+$|^[ivxlcdm]+$", l.lower()) for l in lines):
            return True

    # Critical Guard: Protect abstract, hardware, inputs, equipment, methodology, architecture
    is_protected = any(k in t for k in [
        "hardware", "equipment", "microcontroller", "sensor", "sensors", 
        "arduino", "analog ph", "ec sensor", "ultrasonic", "inputs:", "outputs:",
        "methodology", "architecture", "system overview", "framework", "database", "abstract"
    ])

    # 2. Acknowledgement / กิตติกรรมประกาศ (pure gratitude / signatures)
    if "acknowledgement" in t or "กิตติกรรมประกาศ" in t:
        if not is_protected or ("support of the advisor" in t or "grateful to our parents" in t or len(text) < 450):
            return True

    # 3. Pure References / Bibliography / URL lists
    if any(k in t for k in ["references", "เอกสารอ้างอิง", "bibliography"]):
        url_count = len(re.findall(r"https?://|www\.|doi\.org|\[\d+\]", t))
        ref_markers = len(re.findall(r"(?:vol\.|pp\.|accessed:|retrieved from|edition|press|ieee|acm)", t))
        if (url_count >= 2 or ref_markers >= 2) and not is_protected:
            return True

    # 4. Table of Contents / List of Tables / List of Figures / Working Plan (Gantt Chart)
    if any(k in t for k in ["list of tables", "list of figures", "table of contents", "สารบัญ", "working plan"]):
        toc_lines = [
            l for l in lines
            if any(k in l.lower() for k in ["table", "figure", "page", "chapter", "working plan", "acknowledgement", ".....", "....", "week", "month"])
        ]
        if len(toc_lines) / max(len(lines), 1) > 0.35 and not is_protected:
            return True

    # 5. Appendix title pages without technical content
    if "appendix" in t or "ภาคผนวก" in t:
        if len(lines) <= 4 and not is_protected:
            return True

    # 6. Committee signatures & degree requirements boilerplate
    if "examining committee" in t and len(text) < 500 and not is_protected:
        return True
    if "partial fulfillment of the requirements" in t and len(text) < 450 and not is_protected:
        return True

    return False


def _filter_boilerplate_candidates(results: list[dict]) -> list[dict]:
    """Filter out non-technical boilerplate chunks before passing to Reranker."""
    filtered = [r for r in results if not is_boilerplate_text(r.get("text", ""))]
    return filtered if len(filtered) >= 4 else results


def _diversify_candidates_by_project(results: list[dict], max_per_project: int = 2) -> list[dict]:
    """Ensure candidate pool has diverse representation across distinct projects."""
    proj_counts: dict[str, int] = {}
    diversified: list[dict] = []
    for item in results:
        payload = item.get("payload", {}) or {}
        proj_key = str(payload.get("source") or payload.get("project_title") or payload.get("title", "")).strip()
        count = proj_counts.get(proj_key, 0)
        if count < max_per_project:
            diversified.append(item)
            proj_counts[proj_key] = count + 1
    return diversified if len(diversified) >= 6 else results


def search(query: str, chat_history: str | None = None) -> list[str]:
    print("\n" + "=" * 60)
    print("ORIGINAL QUERY:", query)

    # 1. Use LLM Query Normalizer & Filter Extractor & Intent Classifier
    clean_query, filters, intent = process_query_with_llm(query, chat_history=chat_history)
    top_k, top_n = _get_routing_params(intent)
    print("NORMALIZED / CLEAN QUERY:", clean_query)
    print("INTENT:", intent)
    print("FILTERS:", filters)

    qdrant_filter = build_qdrant_filter(filters)
    print("QDRANT FILTER:", qdrant_filter)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    if not results:
        print("No results after semantic + filter")
        return []

    results = _filter_boilerplate_candidates(results)

    if intent in {"RECOMMENDATION", "EXPLORATORY"}:
        results = _diversify_candidates_by_project(results, max_per_project=2)

    print(f"Retrieved (before rerank): {len(results)} docs")

    reranked = rerank(clean_query, results, top_n)
    print(f"Top after rerank: {len(reranked)} docs")

    return [result["text"] for result in reranked]


def _filter_recommendation_candidates(results: list[dict], target_domains: list[str]) -> list[dict]:
    """Filter out completely irrelevant projects that don't match target domains for RECOMMENDATION."""
    if not target_domains or not results:
        return results

    domain_keywords = {
        "web": ["web", "platform", "portal", "website", "online", "application", "browser", "dashboard", "frontend", "backend", "react", "html", "php", "javascript", "flask", "django"],
        "iot": ["iot", "sensor", "hardware", "arduino", "esp32", "microcontroller", "actuator", "device", "rfid", "ble", "bluetooth", "watering", "hydroponic"],
        "automation": ["automation", "automatic", "automated", "control", "monitoring", "adjust", "mixing", "schedule", "timer"],
        "machine learning": ["machine learning", "model", "prediction", "predict", "classification", "clustering", "regression", "accuracy", "dataset", "training"],
        "energy": ["energy", "saving", "power", "access point", "ap", "sleep", "wifi", "wlan", "consumption"],
        "mobile": ["mobile", "android", "ios", "app", "tracking", "gps", "vehicle", "car", "location"],
        "healthcare": ["health", "hospital", "patient", "discharge", "medical", "clinic", "nurse", "doctor"],
        "cybersecurity": ["security", "penetration", "testing", "vulnerability", "attack", "kali", "exploit", "cve"],
    }

    req_words = set()
    for d in target_domains:
        req_words.update(domain_keywords.get(d.lower(), [d.lower()]))

    matched = []
    unmatched = []
    for item in results:
        txt = (item.get("text", "") + " " + str(item.get("payload", {}))).lower()
        if any(w in txt for w in req_words):
            matched.append(item)
        else:
            unmatched.append(item)

    return matched if matched else results


def search_with_details(query: str, chat_history: str | None = None) -> dict:
    """Search and return detailed results with scores, timing, and dynamic routing intent."""
    total_start = time.perf_counter()
    try:
        print("\n" + "=" * 60)
        print("ORIGINAL QUERY:", query)

        # 1. Use LLM Query Normalizer & Filter Extractor & Intent Classifier
        query_proc_start = time.perf_counter()
        normalized_query, filters, intent = process_query_with_llm(query, chat_history=chat_history)
        query_proc_seconds = time.perf_counter() - query_proc_start
        clean_query = normalized_query
        top_k, top_n = _get_routing_params(intent)
        print("NORMALIZED / CLEAN QUERY:", clean_query)
        print("INTENT:", intent)
        print("FILTERS:", filters)

        retrieval_start = time.perf_counter()
        if intent == "COMPARISON":
            compared = filters.get("compared_projects", [])
            if len(compared) >= 2:
                per_proj_k = max(15, top_k // len(compared))
                all_results = []
                seen_texts = set()
                for p_title in compared:
                    p_filters = {"project_title": p_title}
                    p_res = semantic_search(f"{p_title} overview methodology architecture features technology limitations", per_proj_k, metadata_filters=p_filters)
                    if not p_res:
                        p_res = semantic_search(p_title, per_proj_k, metadata_filters=p_filters)
                    for item in p_res:
                        txt = item.get("text")
                        if txt not in seen_texts:
                            seen_texts.add(txt)
                            all_results.append(item)
                results = all_results if all_results else semantic_search(clean_query, top_k)
            else:
                sub_queries = [p.strip() for p in re.split(r"\s+(?:vs|versus|กับ|and)\s+", clean_query, flags=re.IGNORECASE) if p.strip()]
                if len(sub_queries) >= 2:
                    split_k = max(15, top_k // len(sub_queries))
                    all_results = []
                    seen_texts = set()
                    for sq in sub_queries:
                        sq_res = semantic_search(sq, split_k)
                        for item in sq_res:
                            txt = item.get("text")
                            if txt not in seen_texts:
                                seen_texts.add(txt)
                                all_results.append(item)
                    results = all_results if all_results else semantic_search(clean_query, top_k)
                else:
                    results = semantic_search(clean_query, top_k)
        else:
            results = semantic_search(clean_query, top_k, metadata_filters=filters)
        retrieval_seconds = time.perf_counter() - retrieval_start

        results = _filter_boilerplate_candidates(results)

        if intent == "RECOMMENDATION":
            target_domains = filters.get("target_domains", [])
            if target_domains:
                results = _filter_recommendation_candidates(results, target_domains)
            results = _diversify_candidates_by_project(results, max_per_project=2)
        elif intent == "EXPLORATORY" and results:
            results = _diversify_candidates_by_project(results, max_per_project=2)

        print(f"Retrieved (before rerank): {len(results)} results")

        if not results:
            print("No results after semantic + filter")
            total_seconds = time.perf_counter() - total_start
            return {
                "results": [],
                "errors": [],
                "timing": {
                    "query_proc_seconds": query_proc_seconds,
                    "retrieval_seconds": retrieval_seconds,
                    "rerank_seconds": 0.0,
                    "total_seconds": total_seconds,
                },
                "normalized_query": normalized_query,
                "filters": filters,
                "intent": intent,
                "query_variants": [],
                "retrieved_count": 0,
            }

        try:
            rerank_start = time.perf_counter()
            reranked = rerank(clean_query, results, top_n)
            rerank_seconds = time.perf_counter() - rerank_start
            print(f"\n🎯 [RERANK] Top {len(reranked)} Results (Full Chunks):")
            print("=" * 70)
            for i, result in enumerate(reranked, 1):
                payload = result.get("payload", {})
                score = result.get("score", 0.0)
                source = payload.get("source", "Unknown")
                page = payload.get("page_number", "?")
                title = payload.get("project_title") or payload.get("title", "-")
                advisor = payload.get("advisor", "-")
                author = payload.get("author", "-")

                print(f"📄 Chunk #{i} | Rerank Score: {score:.4f}")
                print(f"   ├─ Source: {source} (Page {page})")
                print(f"   ├─ Title: {title}")
                print(f"   ├─ Author: {author} | Advisor: {advisor}")
                print("   └─ Content:")
                clean_text = result["text"].replace("\r\n", "\n").replace("\r", "\n")
                for line in clean_text.strip().split("\n"):
                    print(f"      {line}")
                print("-" * 70)
        except (TypeError, ValueError, RuntimeError, AttributeError) as e:
            print(f"Error during reranking: {e}")
            rerank_seconds = 0.0
            reranked = results[:top_n]  # Fallback to top semantic results

        total_seconds = time.perf_counter() - total_start
        return {
            "results": reranked,
            "filters": filters,
            "intent": intent,
            "errors": [],
            "timing": {
                "query_proc_seconds": query_proc_seconds,
                "retrieval_seconds": retrieval_seconds,
                "rerank_seconds": rerank_seconds,
                "total_seconds": total_seconds,
            },
            "normalized_query": normalized_query,
            "query_variants": [],
            "retrieved_count": len(results),
        }
    except (TypeError, ValueError, RuntimeError, AttributeError) as exc:
        error_msg = str(exc)
        print(f"Error in search_with_details: {error_msg}")
        total_seconds = time.perf_counter() - total_start
        return {
            "results": [],
            "errors": [error_msg],
            "intent": "FACTOID",
            "timing": {
                "query_proc_seconds": 0.0,
                "retrieval_seconds": 0.0,
                "rerank_seconds": 0.0,
                "total_seconds": total_seconds,
            },
            "normalized_query": query,
            "query_variants": [],
            "retrieved_count": 0,
        }


def hybrid_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    top_n: int = DEFAULT_TOP_N,
    metadata_filters: dict | None = None,
) -> list[dict]:
    """Compatibility wrapper for the current semantic-search plus rerank pipeline."""
    clean_query, filters, _ = process_query_with_llm(query)

    if metadata_filters:
        filters.update(metadata_filters)

    results = semantic_search(clean_query, top_k, metadata_filters=filters)
    return rerank(clean_query, results, top_n)
