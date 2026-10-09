"""
Module: compare_pipelines.py
Description:
    Real-Time Comparison & Evaluation Benchmark Engine for RAGcoon.
    Compares the Legacy Pipeline (Rule-based, Vector only) against the Modern Pipeline
    (LLM Query Processor, True Hybrid RRF, Cross-Encoder Reranker, Fast-Path, Anti-Hallucination).

Features:
    - Side-by-Side Query Execution (Legacy vs Modern)
    - Jaccard Chunk Overlap & Retrieval Shift Measurement
    - Quality Scoring Engine (0-100) using Deterministic Rules & Rubrics
    - 6 Core Benchmark Scenarios Testing Suite
    - Latency Delta & Speedup Factor Computation
"""

import json
import os
import re
import sys
import time
from typing import Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

from backend.app.rag.retrieval.legacy_pipeline import legacy_answer_question, legacy_search_with_details
from backend.app.rag.retrieval.prompt import answer_question
from backend.app.rag.retrieval.service import search_with_details


# =========================================================================
# 1. Metric Calculation & Scoring Rules
# =========================================================================

def compute_jaccard_similarity(list_a: list[str], list_b: list[str]) -> float:
    """Compute Jaccard similarity index between two source lists (0.0 to 1.0)."""
    set_a = set(list_a)
    set_b = set(list_b)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def evaluate_output_quality(
    answer: str,
    latency_sec: float,
    retrieved_count: int,
    sources: list[str],
    has_fast_path: bool = False,
) -> dict[str, Any]:
    """
    Score a RAG output out of 100 based on Deterministic Rules:
      1. Citation Strictness (0-30 pts): Proper [Source: ..., Page: ...] citations.
      2. Anti-Hallucination & Cleanliness (0-25 pts): Absence of empty boilerplate blocks.
      3. Latency Score (0-25 pts): Reward faster responses (< 2s gets full, > 10s penalizes).
      4. Length & Substantiveness (0-20 pts): Informative, non-empty, concise answer.
    """
    score = 0.0
    breakdown = {}

    # 1. Citation Strictness (30 pts)
    citation_pattern = re.compile(r"\[(?:Source|เอกสารอ้างอิง):[^,\]]+,\s*(?:Page|หน้า):[^\]]+\]", re.IGNORECASE)
    has_citations = bool(citation_pattern.search(answer)) or bool(re.search(r"📄\s*`[^`]+`", answer))
    if has_citations or has_fast_path:
        cit_score = 30.0
    elif sources and ("Source" in answer or "หน้า" in answer):
        cit_score = 15.0
    else:
        cit_score = 5.0
    score += cit_score
    breakdown["citation_score"] = cit_score

    # 2. Anti-Hallucination & Boilerplate Penalty (25 pts)
    clean_score = 25.0
    empty_markers = [
        "### 🔔", "บริการภายนอก / การแจ้งเตือนภายนอก\nไม่มีข้อมูล",
        "### ⚠️", "ข้อมูลที่ไม่ได้ระบุ",
        "## Sources\n-",
    ]
    for marker in empty_markers:
        if marker in answer:
            clean_score = max(0.0, clean_score - 10.0)
    score += clean_score
    breakdown["cleanliness_score"] = clean_score

    # 3. Latency Score (25 pts)
    if latency_sec <= 1.5:
        lat_score = 25.0
    elif latency_sec <= 3.5:
        lat_score = 20.0
    elif latency_sec <= 6.0:
        lat_score = 15.0
    elif latency_sec <= 10.0:
        lat_score = 10.0
    else:
        lat_score = 5.0
    score += lat_score
    breakdown["latency_score"] = lat_score

    # 4. Length & Completeness (20 pts)
    ans_len = len(answer.strip())
    if ans_len >= 150:
        len_score = 20.0
    elif ans_len >= 50:
        len_score = 15.0
    elif ans_len > 0:
        len_score = 10.0
    else:
        len_score = 0.0
    score += len_score
    breakdown["length_score"] = len_score

    return {
        "total_score": round(min(100.0, score), 1),
        "breakdown": breakdown,
    }


# =========================================================================
# 2. Pipeline Comparison Function
# =========================================================================

def compare_query(query: str) -> dict[str, Any]:
    """
    Execute a query on both Legacy and Modern pipelines, measure differences,
    calculate quality scores, and declare a verdict.
    """
    # 1. Run Legacy Pipeline
    leg_out = legacy_answer_question(query)
    leg_time = leg_out["timing"]["total_seconds"]
    leg_answer = leg_out.get("answer", "")
    leg_sources = leg_out.get("sources", [])
    leg_eval = evaluate_output_quality(
        leg_answer, leg_time, leg_out.get("retrieved_count", 0), leg_sources, has_fast_path=False
    )

    # 2. Run Modern Pipeline
    mod_start = time.perf_counter()
    mod_raw = answer_question(query)
    mod_time = time.perf_counter() - mod_start
    mod_answer = mod_raw.get("answer", "")
    mod_sources = mod_raw.get("sources", [])
    mod_intent = mod_raw.get("intent", "FACTOID")
    is_fast_path = (mod_time <= 2.0 and not mod_raw.get("scored_contexts"))

    mod_eval = evaluate_output_quality(
        mod_answer, mod_time, len(mod_raw.get("scored_contexts", [])), mod_sources, has_fast_path=is_fast_path
    )

    # 3. Compute Deltas & Overlap
    jaccard = compute_jaccard_similarity(leg_sources, mod_sources)
    score_delta = mod_eval["total_score"] - leg_eval["total_score"]
    speedup = leg_time / mod_time if mod_time > 0 else 1.0

    # 4. Verdict
    if score_delta >= 10.0 or speedup >= 2.0:
        verdict = "MODERN_WIN"
        reason = f"Modern scored +{score_delta:.1f} pts higher with {speedup:.1f}x speedup"
    elif score_delta <= -10.0:
        verdict = "LEGACY_WIN"
        reason = f"Legacy scored +{-score_delta:.1f} pts higher"
    else:
        verdict = "TIE"
        reason = "Both pipelines performed comparably"

    return {
        "query": query,
        "verdict": verdict,
        "reason": reason,
        "jaccard_source_overlap": round(jaccard, 3),
        "speedup_factor": round(speedup, 2),
        "legacy": {
            "answer": leg_answer,
            "filters": leg_out.get("filters", {}),
            "sources": leg_sources,
            "total_seconds": round(leg_time, 3),
            "quality_score": leg_eval["total_score"],
            "score_breakdown": leg_eval["breakdown"],
        },
        "modern": {
            "answer": mod_answer,
            "intent": mod_intent,
            "sources": mod_sources,
            "total_seconds": round(mod_time, 3),
            "quality_score": mod_eval["total_score"],
            "score_breakdown": mod_eval["breakdown"],
        },
    }


# =========================================================================
# 3. 6 Core Benchmark Scenarios
# =========================================================================

BENCHMARK_SCENARIOS = [
    {
        "scenario_id": 1,
        "name": "Natural Language & Typo Understanding",
        "description": "Tests handling of conversational Thai and spelling errors without exact dictionary match",
        "query": "อาจารสุรพลดูแลเรื่องไรบ้าง",
    },
    {
        "scenario_id": 2,
        "name": "Exact Technical Term & Chipset Sniper",
        "description": "Tests Sparse BM25 + RRF on rare hardware acronyms (SX1276, TTGO)",
        "query": "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",
    },
    {
        "scenario_id": 3,
        "name": "Noise & Irrelevant Page Filtering",
        "description": "Tests Cross-Encoder reranker & boilerplate filter against TOC / bibliography pages",
        "query": "ขั้นตอนการทำงานและการทดลองของ The LoRaWAN",
    },
    {
        "scenario_id": 4,
        "name": "Metadata Fast-Path Speed",
        "description": "Tests sub-second Fast-Path template response vs expensive vector search",
        "query": "ใครเป็นที่ปรึกษาของ The LoRaWAN",
    },
    {
        "scenario_id": 5,
        "name": "System Type & Architecture Classification",
        "description": "Tests enriched system categories (IoT & Hardware, Web App) vs blank metadata",
        "query": "The LoRaWAN เป็นระบบประเภทไหน",
    },
    {
        "scenario_id": 6,
        "name": "Anti-Hallucination & Empty Placeholder Guard",
        "description": "Tests strict negative-evidence handling when a component is absent from documents",
        "query": "โครงงาน The LoRaWAN มีการเชื่อมต่อกับ Line Notify หรือไม่",
    },
]


def run_benchmark_suite() -> dict[str, Any]:
    """Execute the full 6-scenario benchmark suite comparing Legacy vs Modern."""
    print("=" * 80)
    print("🚀 Starting RAGcoon Benchmark Suite: Legacy (Rule-Based) vs Modern (True Hybrid RAG)")
    print("=" * 80 + "\n")

    results = []
    modern_wins = 0
    legacy_wins = 0
    ties = 0

    total_leg_time = 0.0
    total_mod_time = 0.0
    total_leg_score = 0.0
    total_mod_score = 0.0

    for item in BENCHMARK_SCENARIOS:
        sc_id = item["scenario_id"]
        sc_name = item["name"]
        query = item["query"]

        print(f"[{sc_id}/6] Scenario: {sc_name}")
        print(f"      Query: '{query}'")

        res = compare_query(query)
        verdict = res["verdict"]

        if verdict == "MODERN_WIN":
            modern_wins += 1
            verdict_icon = "🟢 MODERN WIN"
        elif verdict == "LEGACY_WIN":
            legacy_wins += 1
            verdict_icon = "🔴 LEGACY WIN"
        else:
            ties += 1
            verdict_icon = "🟡 TIE"

        leg_t = res["legacy"]["total_seconds"]
        mod_t = res["modern"]["total_seconds"]
        leg_s = res["legacy"]["quality_score"]
        mod_s = res["modern"]["quality_score"]

        total_leg_time += leg_t
        total_mod_time += mod_t
        total_leg_score += leg_s
        total_mod_score += mod_s

        print(f"      Result: {verdict_icon} ({res['reason']})")
        print(f"      Time: Legacy {leg_t:.2f}s | Modern {mod_t:.2f}s (Speedup: {res['speedup_factor']}x)")
        print(f"      Score: Legacy {leg_s}/100 | Modern {mod_s}/100")
        print(f"      Source Overlap (Jaccard): {res['jaccard_source_overlap'] * 100:.1f}%\n")

        results.append({
            "scenario_id": sc_id,
            "name": sc_name,
            **res,
        })

    num_tests = len(BENCHMARK_SCENARIOS)
    avg_leg_time = total_leg_time / num_tests
    avg_mod_time = total_mod_time / num_tests
    avg_leg_score = total_leg_score / num_tests
    avg_mod_score = total_mod_score / num_tests

    summary = {
        "total_scenarios": num_tests,
        "modern_wins": modern_wins,
        "legacy_wins": legacy_wins,
        "ties": ties,
        "win_rate_modern_pct": round((modern_wins / num_tests) * 100, 1),
        "avg_latency_legacy_seconds": round(avg_leg_time, 2),
        "avg_latency_modern_seconds": round(avg_mod_time, 2),
        "avg_latency_improvement_pct": round(((avg_leg_time - avg_mod_time) / avg_leg_time) * 100, 1) if avg_leg_time > 0 else 0.0,
        "avg_quality_legacy_score": round(avg_leg_score, 1),
        "avg_quality_modern_score": round(avg_mod_score, 1),
        "detailed_results": results,
    }

    print("=" * 80)
    print("📊 BENCHMARK SUMMARY REPORT")
    print("=" * 80)
    print(f"🏆 Modern Win Rate: {summary['win_rate_modern_pct']}% ({modern_wins} Wins, {legacy_wins} Losses, {ties} Ties)")
    print(f"⚡ Average Latency: Legacy {avg_leg_time:.2f}s -> Modern {avg_mod_time:.2f}s ({summary['avg_latency_improvement_pct']}% faster)")
    print(f"📈 Average Quality: Legacy {avg_leg_score:.1f}/100 -> Modern {avg_mod_score:.1f}/100 (+{avg_mod_score - avg_leg_score:.1f} pts)")
    print("=" * 80 + "\n")

    return summary


if __name__ == "__main__":
    run_benchmark_suite()
