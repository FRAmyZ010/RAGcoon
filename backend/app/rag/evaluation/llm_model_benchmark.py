"""
Module: llm_model_benchmark.py
Description:
    Multi-LLM Model Benchmark Engine for RAGcoon on RTX 3050 Ti (4GB VRAM) + 16GB RAM.
    Compares 7 Local Ollama Models under the locked Optimal RAG Configuration:
      1. gemma3:4b   (3.3 GB - Google Balanced 4B Baseline)
      2. qwen3:4b    (2.5 GB - Alibaba Reasoning 4B)
      3. qwen2.5:3b  (1.9 GB - Alibaba Ultra-Fast 3B)
      4. llama3.2:3b (2.0 GB - Meta Compact 3B)
      5. gemma3:1b   (0.8 GB - Google Ultra-Lightweight 1B)
      6. qwen2.5:7b  (4.7 GB - Alibaba High-Capacity 7B)
      7. llama3.1:8b (4.9 GB - Meta Standard 8B)
"""

import contextlib
import io
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import app.rag.evaluation.parameter_sweep as ps
from app.rag.retrieval.prompt import answer_question
from app.rag.retrieval.rag_config import RAGConfig
from app.rag.retrieval.service import search_with_details
from app.rag.evaluation.config_benchmark import (
    _calculate_phrase_recall,
    _check_hallucination_guard,
    _check_retrieval_hit,
)
from app.rag.evaluation.compare_pipelines import evaluate_output_quality
from app.rag.evaluation.export_parameter_sweep_excel import compute_rubric_breakdown

RESULTS_JSON = os.path.join(CURRENT_DIR, "results", "parameter_sweep_results.json")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MODEL_SPECS = [
    {
        "model": "gemma3:4b",
        "family": "Google Gemma 3",
        "params": "4.3B",
        "size_gb": 3.3,
        "vram_fit": "🟢 100% GPU (พอดี VRAM 4GB)",
        "vram_score": 90.0,
        "role": "Baseline หลัก (สมดุลภาษาไทย-อังกฤษ + โครงสร้าง Markdown)",
    },
    {
        "model": "qwen2.5:3b",
        "family": "Alibaba Qwen 2.5",
        "params": "3.1B",
        "size_gb": 1.9,
        "vram_fit": "🟢 100% GPU (เบาพิเศษ เหลือ VRAM 2.1GB)",
        "vram_score": 98.0,
        "role": "เน้นความเร็วสูงสุดบน RTX 3050 Ti + แม่นคีย์เวิร์ดไทย/อังกฤษ",
    },
    {
        "model": "qwen3:4b",
        "family": "Alibaba Qwen 3",
        "params": "4.0B",
        "size_gb": 2.5,
        "vram_fit": "🟢 100% GPU (เหลือ VRAM 1.5GB)",
        "vram_score": 95.0,
        "role": "รุ่นใหม่เน้นการคิดเชิงเหตุผล (Reasoning) และการสกัดข้อมูลเทคนิค",
    },
    {
        "model": "llama3.2:3b",
        "family": "Meta Llama 3.2",
        "params": "3.2B",
        "size_gb": 2.0,
        "vram_fit": "🟢 100% GPU (เหลือ VRAM 2.0GB)",
        "vram_score": 97.0,
        "role": "รุ่นเล็กของ Meta สำหรับ Laptop GPU 4GB (เด่นภาษาอังกฤษ)",
    },
    {
        "model": "gemma3:1b",
        "family": "Google Gemma 3",
        "params": "1.0B",
        "size_gb": 0.8,
        "vram_fit": "🟢 100% GPU (จิ๋วพิเศษ กิน VRAM < 1GB)",
        "vram_score": 100.0,
        "role": "Ultra-Lightweight ทดสอบขีดจำกัดความเร็วสูงสุดเมื่อลดขนาดเหลือ 1B",
    },
    {
        "model": "qwen2.5:7b",
        "family": "Alibaba Qwen 2.5",
        "params": "7.6B",
        "size_gb": 4.7,
        "vram_fit": "🟡 Hybrid GPU+CPU (เกิน VRAM 4GB เล็กน้อย)",
        "vram_score": 70.0,
        "role": "ตัวแทนรุ่นกลาง 7B ความเข้าใจลึกซึ้งแต่ใช้เวลาประมวลผลนานขึ้น",
    },
    {
        "model": "llama3.1:8b",
        "family": "Meta Llama 3.1",
        "params": "8.0B",
        "size_gb": 4.9,
        "vram_fit": "🟡 Hybrid GPU+CPU (เกิน VRAM 4GB ต้องพึ่ง RAM)",
        "vram_score": 65.0,
        "role": "ตัวแทนรุ่นใหญ่ 8B มาตรฐานของ Meta",
    },
]


def build_gemma3_4b_from_stage2(
    spec: dict[str, Any],
    test_cases: list[dict[str, Any]],
    stage2_row: dict[str, Any],
) -> dict[str, Any]:
    tc_map = {tc["id"]: tc for tc in test_cases}
    cit_scores, clean_scores, lat_scores, comp_scores, rubric_totals = [], [], [], [], []
    quality_scores, phrase_recalls, halluc_passes = [], [], []
    in_tokens_list, out_tokens_list, llm_sec_list, tps_list = [], [], [], []
    per_query_records = []

    for pq in stage2_row.get("per_query", []):
        qid = pq["id"]
        tc = tc_map.get(qid, {})
        ans = pq.get("answer_preview", "")
        llm_s = float(pq.get("llm_seconds", 0.0))
        tot_s = float(pq.get("total_seconds", 0.0))
        in_tok = int(pq.get("input_tokens", 0))
        out_tok = int(pq.get("output_tokens", 0))
        tps = round(out_tok / llm_s, 1) if llm_s > 0 and out_tok > 0 else 0.0
        phrase_rec_pct = float(pq.get("phrase_recall_pct", 0.0))
        halluc_pct = 100.0 if pq.get("hallucination_guard", 1) else 0.0
        qual = float(pq.get("quality_score", 0.0))

        is_fp = qid == "GT-04"
        rub = compute_rubric_breakdown(ans, tot_s, is_fast_path=is_fp)
        cit_scores.append(rub["citation_30"])
        clean_scores.append(rub["cleanliness_25"])
        lat_scores.append(rub["latency_25"])
        comp_scores.append(rub["completeness_20"])
        rubric_totals.append(rub["rubric_total_100"])
        quality_scores.append(qual)
        phrase_recalls.append(phrase_rec_pct)
        halluc_passes.append(halluc_pct)
        in_tokens_list.append(in_tok)
        out_tokens_list.append(out_tok)
        llm_sec_list.append(llm_s)
        if tps > 0:
            tps_list.append(tps)

        per_query_records.append({
            "id": qid,
            "category": pq.get("category", tc.get("category", "")),
            "query": tc.get("query", ""),
            "citation_30": rub["citation_30"],
            "cleanliness_25": rub["cleanliness_25"],
            "latency_25": rub["latency_25"],
            "completeness_20": rub["completeness_20"],
            "rubric_total_100": rub["rubric_total_100"],
            "phrase_recall_pct": round(phrase_rec_pct, 1),
            "hallucination_guard_pct": halluc_pct,
            "quality_score": round(qual, 2),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "llm_seconds": round(llm_s, 2),
            "total_seconds": round(tot_s, 2),
            "tps": tps,
            "answer_preview": ans,
        })

    n = max(len(per_query_records), 1)
    avg_cit = sum(cit_scores) / n
    avg_clean = sum(clean_scores) / n
    avg_lat = sum(lat_scores) / n
    avg_comp = sum(comp_scores) / n
    avg_rubric = sum(rubric_totals) / n
    avg_quality = float(stage2_row.get("avg_quality_score", sum(quality_scores) / n))
    avg_phrase = float(stage2_row.get("avg_phrase_recall_pct", sum(phrase_recalls) / n))
    avg_halluc = float(stage2_row.get("avg_hallucination_pass_pct", sum(halluc_passes) / n))
    avg_mp = float(stage2_row.get("multi_project_coverage_pct", 100.0))
    avg_in_tok = float(stage2_row.get("avg_input_tokens", sum(in_tokens_list) / n))
    avg_out_tok = float(stage2_row.get("avg_output_tokens", sum(out_tokens_list) / n))
    avg_llm_s = float(stage2_row.get("avg_llm_seconds", sum(llm_sec_list) / n))
    avg_tps = float(stage2_row.get("avg_tps", sum(tps_list) / len(tps_list) if tps_list else 12.4))

    speed_score = max(0.0, min(100.0, 100.0 * (1.0 - max(0.0, avg_llm_s - 2.0) / 23.0)))
    vram_score = float(spec["vram_score"])
    accuracy_blend = 0.70 * avg_phrase + 0.30 * avg_mp
    suitability_composite = (
        0.45 * avg_quality
        + 0.25 * accuracy_blend
        + 0.15 * speed_score
        + 0.15 * vram_score
    )
    return {
        "model": spec["model"],
        "family": spec["family"],
        "params": spec["params"],
        "size_gb": spec["size_gb"],
        "vram_fit": spec["vram_fit"],
        "vram_score": vram_score,
        "role": spec["role"],
        "avg_citation_30": round(avg_cit, 1),
        "avg_cleanliness_25": round(avg_clean, 1),
        "avg_latency_25": round(avg_lat, 1),
        "avg_completeness_20": round(avg_comp, 1),
        "avg_rubric_100": round(avg_rubric, 1),
        "avg_quality_score": round(avg_quality, 2),
        "avg_phrase_recall_pct": round(avg_phrase, 2),
        "avg_hallucination_pass_pct": round(avg_halluc, 2),
        "multi_project_coverage_pct": round(avg_mp, 2),
        "avg_input_tokens": round(avg_in_tok, 1),
        "avg_output_tokens": round(avg_out_tok, 1),
        "avg_llm_seconds": round(avg_llm_s, 2),
        "avg_tps": round(avg_tps, 1),
        "speed_score": round(speed_score, 2),
        "composite_score": round(suitability_composite, 2),
        "per_query": per_query_records,
    }


def evaluate_model_on_suite(
    spec: dict[str, Any],
    test_cases: list[dict[str, Any]],
    cached_retrievals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    model_name = spec["model"]
    max_tok = 160 if spec["size_gb"] > 4.0 else 200
    cfg = RAGConfig(
        profile_name=f"llm_bench_{model_name.replace(':', '_')}",
        description=f"Multi-LLM Benchmark: {model_name} ({spec['size_gb']} GB) - {spec['role']}",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
        max_context_chunks=6,
        max_chunks_per_project=2,
        llm_provider="ollama",
        llm_model=model_name,
        temperature=0.0,
        num_predict=max_tok,
        prompt_preset="balanced",
    )

    cit_scores = []
    clean_scores = []
    lat_scores = []
    comp_scores = []
    rubric_totals = []
    quality_scores = []
    phrase_recalls = []
    halluc_passes = []
    multi_proj_scores = []
    in_tokens_list = []
    out_tokens_list = []
    llm_sec_list = []
    tps_list = []
    per_query_records = []

    for tc in test_cases:
        qid = tc["id"]
        query = tc["query"]
        pre_ret = cached_retrievals[qid]

        with contextlib.redirect_stdout(io.StringIO()):
            response = answer_question(
                question=query,
                session_id=None,
                llm_provider="ollama",
                llm_model=model_name,
                config=cfg,
                precomputed_retrieval=pre_ret,
            )

        answer = str(response.get("answer", ""))
        sources = response.get("sources", []) or []
        timing = response.get("timing", {}) or {}
        perf = response.get("performance", {}) or {}
        tb = perf.get("token_breakdown", {}) or {}

        llm_s = float(timing.get("llm_seconds", 0.0))
        tot_s = float(timing.get("total_seconds", 0.0))
        in_tok = int(perf.get("input_tokens", 0) or perf.get("prompt_eval_count", 0) or tb.get("document_context_tokens", 0))
        out_tok = int(perf.get("output_tokens", 0) or perf.get("eval_count", 0))
        tps = float(perf.get("gen_speed_tps", 0.0))

        key_phrases = tc.get("key_phrases", [])
        should_reject = bool(tc.get("should_reject", False))
        forbidden_phrases = [fp.lower() for fp in tc.get("forbidden_phrases", [])]

        phrase_rec_pct = _calculate_phrase_recall(answer, key_phrases)
        guard_ok = _check_hallucination_guard(answer, should_reject)
        if forbidden_phrases and any(fp in answer.lower() for fp in forbidden_phrases):
            guard_ok = False
        halluc_pct = 100.0 if guard_ok else 0.0

        is_fp = qid == "GT-04"
        rub = compute_rubric_breakdown(answer, tot_s, is_fast_path=is_fp)
        blended_quality = round(0.60 * rub["rubric_total_100"] + 0.25 * phrase_rec_pct + 0.15 * halluc_pct, 2)

        if qid == "GT-08":
            ans_low = answer.lower()
            has_p1 = any(k in ans_low for k in ["lora", "lorawan", "sx1276"])
            has_p2 = any(k in ans_low for k in ["beacon", "bsld", "ble", "bluetooth"])
            mp_cov = 100.0 if (has_p1 and has_p2) else (50.0 if (has_p1 or has_p2) else 0.0)
            multi_proj_scores.append(mp_cov)

        cit_scores.append(rub["citation_30"])
        clean_scores.append(rub["cleanliness_25"])
        lat_scores.append(rub["latency_25"])
        comp_scores.append(rub["completeness_20"])
        rubric_totals.append(rub["rubric_total_100"])
        quality_scores.append(blended_quality)
        phrase_recalls.append(phrase_rec_pct)
        halluc_passes.append(halluc_pct)
        in_tokens_list.append(in_tok)
        out_tokens_list.append(out_tok)
        llm_sec_list.append(llm_s)
        if tps > 0:
            tps_list.append(tps)

        per_query_records.append({
            "id": qid,
            "category": tc.get("category", ""),
            "query": query,
            "citation_30": rub["citation_30"],
            "cleanliness_25": rub["cleanliness_25"],
            "latency_25": rub["latency_25"],
            "completeness_20": rub["completeness_20"],
            "rubric_total_100": rub["rubric_total_100"],
            "phrase_recall_pct": round(phrase_rec_pct, 1),
            "hallucination_guard_pct": halluc_pct,
            "quality_score": blended_quality,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "llm_seconds": round(llm_s, 2),
            "total_seconds": round(tot_s, 2),
            "tps": round(tps, 1),
            "answer_preview": answer[:240].replace("\n", " "),
        })

    n = max(len(test_cases), 1)
    avg_cit = sum(cit_scores) / n
    avg_clean = sum(clean_scores) / n
    avg_lat = sum(lat_scores) / n
    avg_comp = sum(comp_scores) / n
    avg_rubric = sum(rubric_totals) / n
    avg_quality = sum(quality_scores) / n
    avg_phrase = sum(phrase_recalls) / n
    avg_halluc = sum(halluc_passes) / n
    avg_mp = sum(multi_proj_scores) / len(multi_proj_scores) if multi_proj_scores else 100.0
    avg_in_tok = sum(in_tokens_list) / n
    avg_out_tok = sum(out_tokens_list) / n
    avg_llm_s = sum(llm_sec_list) / n
    avg_tps = sum(tps_list) / len(tps_list) if tps_list else 0.0

    # Speed score: 100 at <=2s, 0 at >=25s
    speed_score = max(0.0, min(100.0, 100.0 * (1.0 - max(0.0, avg_llm_s - 2.0) / 23.0)))
    vram_score = float(spec["vram_score"])

    # Overall LLM Suitability Composite Score:
    # 45% Blended Quality + 25% Key Phrase & Multi-Project Recall + 15% Speed Score + 15% Hardware VRAM Fit Score
    accuracy_blend = 0.70 * avg_phrase + 0.30 * avg_mp
    suitability_composite = (
        0.45 * avg_quality
        + 0.25 * accuracy_blend
        + 0.15 * speed_score
        + 0.15 * vram_score
    )

    return {
        "model": model_name,
        "family": spec["family"],
        "params": spec["params"],
        "size_gb": spec["size_gb"],
        "vram_fit": spec["vram_fit"],
        "vram_score": vram_score,
        "role": spec["role"],
        "avg_citation_30": round(avg_cit, 1),
        "avg_cleanliness_25": round(avg_clean, 1),
        "avg_latency_25": round(avg_lat, 1),
        "avg_completeness_20": round(avg_comp, 1),
        "avg_rubric_100": round(avg_rubric, 1),
        "avg_quality_score": round(avg_quality, 2),
        "avg_phrase_recall_pct": round(avg_phrase, 2),
        "avg_hallucination_pass_pct": round(avg_halluc, 2),
        "multi_project_coverage_pct": round(avg_mp, 2),
        "avg_input_tokens": round(avg_in_tok, 1),
        "avg_output_tokens": round(avg_out_tok, 1),
        "avg_llm_seconds": round(avg_llm_s, 2),
        "avg_tps": round(avg_tps, 1),
        "speed_score": round(speed_score, 2),
        "composite_score": round(suitability_composite, 2),
        "per_query": per_query_records,
    }


def run_multi_llm_benchmark():
    dataset = ps.load_golden_dataset()
    precomputed_queries = ps.build_precomputed_queries(dataset)
    precomputed_queries["GT-08"] = (
        "The LoRaWAN vs BSLD (Beacon Signal Location Device) hardware microcontroller sensors",
        {"compared_projects": ["The LoRaWAN", "BSLD (Beacon Signal Location Device)"]},
        "COMPARISON",
        0.001,
    )

    target_ids = {"GT-01", "GT-03", "GT-04", "GT-06", "GT-08"}
    test_cases = [tc for tc in dataset if tc["id"] in target_ids]

    print("=" * 80, flush=True)
    print("🤖 STARTING MULTI-LLM BENCHMARK ON RTX 3050 Ti (4GB VRAM) + 16GB RAM", flush=True)
    print("=" * 80, flush=True)

    # Pre-fetch retrieval pool once under Optimal Stage 1 Config
    cached_retrievals: dict[str, dict[str, Any]] = {}
    base_ret_cfg = RAGConfig(
        profile_name="optimal_retrieval_lock",
        top_k=15,
        rerank_top_n=10,
        enable_hybrid=True,
        enable_reranker=True,
        enable_boilerplate_filter=True,
        enable_fast_path=True,
    )
    for tc in test_cases:
        qid = tc["id"]
        with contextlib.redirect_stdout(io.StringIO()):
            cached_retrievals[qid] = search_with_details(
                tc["query"],
                config=base_ret_cfg,
                precomputed_query_proc=precomputed_queries[qid],
            )

    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Check if gemma3:4b result from Exp 4 (Chunks=6, Quota=2) can be enriched directly to save time
    stage2_gemma_row = next(
        (r for r in payload.get("stage2_results", []) if r.get("profile_name") == "sweep_chunks_6_quota_2"),
        None,
    )
    llm_results = []
    for spec in MODEL_SPECS:
        m_name = spec["model"]
        print(f"\n⏳ Benchmarking LLM Model: {m_name} ({spec['size_gb']} GB | {spec['vram_fit']})...", flush=True)
        if m_name == "gemma3:4b" and stage2_gemma_row is not None:
            res = build_gemma3_4b_from_stage2(spec, test_cases, stage2_gemma_row)
        else:
            res = evaluate_model_on_suite(spec, test_cases, cached_retrievals)
        llm_results.append(res)
        print(
            f"   👉 [{m_name:12s}] Quality={res['avg_quality_score']:5.1f} | PhraseRecall={res['avg_phrase_recall_pct']:5.1f}% | "
            f"MultiProj={res['multi_project_coverage_pct']:5.1f}% | LLM={res['avg_llm_seconds']:5.2f}s | "
            f"Speed={res['avg_tps']:4.1f} TPS | Suitability={res['composite_score']:5.2f}",
            flush=True,
        )

    # Sort by composite_score descending for ranking
    llm_results_sorted = sorted(llm_results, key=lambda x: x["composite_score"], reverse=True)
    best_llm = llm_results_sorted[0]
    print("\n" + "=" * 80, flush=True)
    print(
        f"🏆 [MULTI-LLM WINNER] {best_llm['model']} ({best_llm['size_gb']} GB) "
        f"| Suitability Score: {best_llm['composite_score']:.2f} | Avg Latency: {best_llm['avg_llm_seconds']:.2f}s",
        flush=True,
    )
    print("=" * 80, flush=True)

    payload["llm_benchmark_results"] = llm_results_sorted
    payload["llm_winner"] = {
        "best_model": best_llm["model"],
        "size_gb": best_llm["size_gb"],
        "suitability_score": best_llm["composite_score"],
        "avg_quality_score": best_llm["avg_quality_score"],
        "avg_phrase_recall_pct": best_llm["avg_phrase_recall_pct"],
        "avg_llm_seconds": best_llm["avg_llm_seconds"],
        "avg_tps": best_llm["avg_tps"],
    }

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "parameter_sweep_results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    from app.rag.evaluation.export_parameter_sweep_excel import build_all_excel_files
    build_all_excel_files()


if __name__ == "__main__":
    run_multi_llm_benchmark()
