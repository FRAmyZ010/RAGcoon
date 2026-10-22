"""
Module: config_benchmark.py
Description:
    RAGcoon Configuration & Hyperparameter Benchmark Engine (Thesis Chapter 4).
    Enables rigorous, empirical comparisons across:
      1. Hyperparameter Sensitivity & Presets (Baseline vs Fast-Mode vs Deep-Academic)
      2. Ablation Studies (Dense Only, No Rerank, No Boilerplate Filter, No Fast Path)
      3. Multi-LLM Model Benchmarking (Ollama Gemma 3, Ollama Qwen 3, Google Gemini, OpenAI ChatGPT)
      4. Ground Truth Evaluation against the 15-case Golden Dataset (golden_dataset.json)

Usage:
    python backend/app/rag/evaluation/config_benchmark.py
    python backend/app/rag/evaluation/config_benchmark.py --baseline precision_hybrid --candidate fast_mode
    python backend/app/rag/evaluation/config_benchmark.py --candidate ablation_dense_only --test-id GT-01,GT-04
    python backend/app/rag/evaluation/config_benchmark.py --models gemma3,qwen3,gemini
"""

import sys
import os
import io
import json
import time
import argparse
from datetime import datetime
from typing import Any, Optional

# Ensure UTF-8 output on Windows PowerShell
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.rag.retrieval.rag_config import (
    RAGConfig,
    CONFIG_PRESETS,
    get_config_preset,
    get_active_config,
    set_active_config,
)
from backend.app.rag.retrieval.prompt import answer_question
from backend.app.rag.evaluation.compare_pipelines import evaluate_output_quality
from backend.app.rag.retrieval.llm_provider import (
    AVAILABLE_LLM_PROFILES,
    get_active_llm,
    set_active_llm,
    test_provider_connectivity,
)

RESULTS_DIR = os.path.join(CURRENT_DIR, "results")
GOLDEN_DATASET_PATH = os.path.join(CURRENT_DIR, "golden_dataset.json")


def load_golden_dataset() -> list[dict[str, Any]]:
    """Load the ground truth test cases."""
    if not os.path.exists(GOLDEN_DATASET_PATH):
        raise FileNotFoundError(f"Golden dataset not found at {GOLDEN_DATASET_PATH}")
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_retrieval_hit(retrieved_sources: list[str], expected_sources: list[str]) -> bool:
    """Return True if at least one expected source is present in retrieved sources."""
    if not expected_sources:
        return True
    ret_set = {s.lower().strip() for s in retrieved_sources if s}
    for exp in expected_sources:
        exp_clean = exp.lower().strip()
        if any(exp_clean in r or r in exp_clean for r in ret_set):
            return True
    return False


def _calculate_phrase_recall(text: str, key_phrases: list[str]) -> float:
    """Calculate the percentage of key ground truth phrases found in generated answer."""
    if not key_phrases:
        return 1.0
    text_lower = text.lower()
    matches = sum(1 for phrase in key_phrases if phrase.lower() in text_lower)
    return round((matches / len(key_phrases)) * 100.0, 1)


def _check_hallucination_guard(answer: str, should_reject: bool) -> bool:
    """Check whether unanswerable/negative questions were safely handled without fabrication."""
    if not should_reject:
        return True
    rejection_markers = [
        "ไม่พบข้อมูล",
        "ไม่มีข้อมูล",
        "ไม่ปรากฏ",
        "no relevant information",
        "not specified",
        "i don't know",
        "ขออภัย",
    ]
    ans_lower = answer.lower()
    return any(marker in ans_lower for marker in rejection_markers)


def run_benchmark_on_item(
    test_case: dict[str, Any],
    config: RAGConfig,
) -> dict[str, Any]:
    """Execute a single golden test case under a specific RAGConfig and collect metrics."""
    query = test_case["query"]
    t0 = time.perf_counter()

    try:
        res = answer_question(
            query,
            config=config,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
        )
        total_time = time.perf_counter() - t0
        answer = res.get("answer", "")
        perf = res.get("performance", {})
        timing = res.get("timing", {})
        sources = res.get("sources", [])
        citations = res.get("citations", [])
        retrieved_count = res.get("retrieved_count", len(sources))

        # Ground Truth Verification
        expected_sources = test_case.get("expected_sources", [])
        key_phrases = test_case.get("key_phrases", [])
        should_reject = test_case.get("should_reject", False)

        hit_rate = 1.0 if _check_retrieval_hit(sources, expected_sources) else 0.0
        phrase_recall = _calculate_phrase_recall(answer, key_phrases)
        guard_passed = _check_hallucination_guard(answer, should_reject)

        # Quality scoring using 5-dimension rubric
        quality_res = evaluate_output_quality(
            answer=answer,
            latency_sec=total_time,
            retrieved_count=retrieved_count,
            sources=sources,
            has_fast_path=bool(res.get("fast_path_used")),
        )

        return {
            "test_id": test_case["id"],
            "category": test_case.get("category", "General"),
            "query": query,
            "config_profile": config.profile_name,
            "success": True,
            "answer": answer,
            "hit_rate": hit_rate,
            "phrase_recall": phrase_recall,
            "guard_passed": guard_passed,
            "quality_score": quality_res["total_score"],
            "score_breakdown": quality_res["breakdown"],
            "retrieved_count": retrieved_count,
            "sources": sources,
            "citations_count": len(citations),
            "fast_path_used": bool(res.get("fast_path_used")),
            "timing": {
                "query_proc_seconds": round(timing.get("query_proc_seconds", 0.0), 4),
                "retrieval_seconds": round(timing.get("retrieval_seconds", 0.0), 3),
                "rerank_seconds": round(timing.get("rerank_seconds", 0.0), 3),
                "llm_seconds": round(timing.get("llm_seconds", 0.0), 3),
                "ttft_seconds": round(perf.get("ttft_seconds", 0.0), 3),
                "total_seconds": round(total_time, 3),
            },
            "throughput": {
                "gen_speed_tps": round(perf.get("gen_speed_tps", 0.0), 1),
                "input_tokens": perf.get("input_tokens", 0),
                "output_tokens": perf.get("output_tokens", 0),
            },
        }
    except Exception as e:
        total_time = time.perf_counter() - t0
        return {
            "test_id": test_case["id"],
            "category": test_case.get("category", "General"),
            "query": query,
            "config_profile": config.profile_name,
            "success": False,
            "answer": f"⚠️ Error: {e}",
            "hit_rate": 0.0,
            "phrase_recall": 0.0,
            "guard_passed": False,
            "quality_score": 0.0,
            "score_breakdown": {},
            "retrieved_count": 0,
            "sources": [],
            "citations_count": 0,
            "fast_path_used": False,
            "timing": {
                "query_proc_seconds": 0.0,
                "retrieval_seconds": 0.0,
                "rerank_seconds": 0.0,
                "llm_seconds": 0.0,
                "ttft_seconds": 0.0,
                "total_seconds": round(total_time, 3),
            },
            "throughput": {
                "gen_speed_tps": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
            "error": str(e),
        }


def run_comparative_benchmark(
    baseline_cfg: RAGConfig,
    candidate_cfg: RAGConfig,
    test_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run full comparative evaluation between Baseline (Config A) and Candidate (Config B).
    Calculates Delta metrics and aggregates for Thesis Chapter 4.
    """
    print("\n" + "=" * 90)
    print(f"🔬 RAGcoon Hyperparameter Benchmark & Comparative Engine")
    print(f"• Baseline Config  (A): [{baseline_cfg.profile_name}] - {baseline_cfg.description}")
    print(f"• Candidate Config (B): [{candidate_cfg.profile_name}] - {candidate_cfg.description}")
    print(f"• จำนวนข้อทดสอบ: {len(test_cases)} ข้อ (จาก golden_dataset.json)")
    print("=" * 90)

    comparisons: list[dict[str, Any]] = []

    for idx, tc in enumerate(test_cases, start=1):
        q_preview = tc['query'][:40] + ("..." if len(tc['query']) > 40 else "")
        print(f"\n[{idx}/{len(test_cases)}] ⏳ กำลังประเมินข้อ {tc['id']}: \"{q_preview}\"")

        # Run Baseline
        print(f"   ├─ รัน Baseline ({baseline_cfg.profile_name}) ...", end="", flush=True)
        res_a = run_benchmark_on_item(tc, baseline_cfg)
        print(f" ได้คะแนน {res_a['quality_score']}/100 ใน {res_a['timing']['total_seconds']}s")

        # Run Candidate
        print(f"   └─ รัน Candidate ({candidate_cfg.profile_name}) ...", end="", flush=True)
        res_b = run_benchmark_on_item(tc, candidate_cfg)
        print(f" ได้คะแนน {res_b['quality_score']}/100 ใน {res_b['timing']['total_seconds']}s")

        # Calculate Deltas
        delta_score = round(res_b["quality_score"] - res_a["quality_score"], 2)
        delta_latency = round(res_b["timing"]["total_seconds"] - res_a["timing"]["total_seconds"], 3)
        time_a = res_a["timing"]["total_seconds"]
        time_b = res_b["timing"]["total_seconds"]
        speedup = round(time_a / time_b, 2) if time_b > 0 and time_a > 0 else 1.0

        comparisons.append({
            "test_id": tc["id"],
            "category": tc.get("category", ""),
            "query": tc["query"],
            "baseline": res_a,
            "candidate": res_b,
            "delta": {
                "score": delta_score,
                "latency_seconds": delta_latency,
                "speedup_ratio": speedup,
                "hit_rate_diff": int(res_b["hit_rate"] - res_a["hit_rate"]),
                "recall_diff": round(res_b["phrase_recall"] - res_a["phrase_recall"], 1),
            },
        })

    # Compute Summary Aggregates
    n = len(comparisons)
    if n > 0:
        avg_score_a = sum(c["baseline"]["quality_score"] for c in comparisons) / n
        avg_score_b = sum(c["candidate"]["quality_score"] for c in comparisons) / n
        avg_time_a = sum(c["baseline"]["timing"]["total_seconds"] for c in comparisons) / n
        avg_time_b = sum(c["candidate"]["timing"]["total_seconds"] for c in comparisons) / n
        avg_hr_a = (sum(c["baseline"]["hit_rate"] for c in comparisons) / n) * 100.0
        avg_hr_b = (sum(c["candidate"]["hit_rate"] for c in comparisons) / n) * 100.0
        avg_recall_a = sum(c["baseline"]["phrase_recall"] for c in comparisons) / n
        avg_recall_b = sum(c["candidate"]["phrase_recall"] for c in comparisons) / n
        avg_speed_a = sum(c["baseline"]["throughput"]["gen_speed_tps"] for c in comparisons) / n
        avg_speed_b = sum(c["candidate"]["throughput"]["gen_speed_tps"] for c in comparisons) / n
    else:
        avg_score_a = avg_score_b = avg_time_a = avg_time_b = 0.0
        avg_hr_a = avg_hr_b = avg_recall_a = avg_recall_b = avg_speed_a = avg_speed_b = 0.0

    delta_avg_score = round(avg_score_b - avg_score_a, 2)
    delta_avg_time = round(avg_time_b - avg_time_a, 3)
    overall_speedup = round(avg_time_a / avg_time_b, 2) if avg_time_b > 0 and avg_time_a > 0 else 1.0

    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline_config": baseline_cfg.to_dict(),
        "candidate_config": candidate_cfg.to_dict(),
        "total_test_cases": n,
        "aggregates": {
            "baseline": {
                "avg_quality_score": round(avg_score_a, 2),
                "avg_total_latency_sec": round(avg_time_a, 3),
                "hit_rate_pct": round(avg_hr_a, 1),
                "key_phrase_recall_pct": round(avg_recall_a, 1),
                "gen_speed_tps": round(avg_speed_a, 1),
            },
            "candidate": {
                "avg_quality_score": round(avg_score_b, 2),
                "avg_total_latency_sec": round(avg_time_b, 3),
                "hit_rate_pct": round(avg_hr_b, 1),
                "key_phrase_recall_pct": round(avg_recall_b, 1),
                "gen_speed_tps": round(avg_speed_b, 1),
            },
            "delta": {
                "score_delta": delta_avg_score,
                "latency_delta_sec": delta_avg_time,
                "speedup_ratio": overall_speedup,
                "hit_rate_delta_pct": round(avg_hr_b - avg_hr_a, 1),
                "recall_delta_pct": round(avg_recall_b - avg_recall_a, 1),
            },
        },
        "comparisons": comparisons,
    }

    _print_comparison_summary(summary)
    return summary


def _print_comparison_summary(report: dict[str, Any]) -> None:
    """Print beautifully formatted comparison table to terminal."""
    agg = report["aggregates"]
    b_name = report["baseline_config"]["profile_name"]
    c_name = report["candidate_config"]["profile_name"]

    print("\n" + "=" * 90)
    print("📊 [ตารางสรุปผลการเปรียบเทียบเชิงประจักษ์ (Empirical Delta Overview)]")
    print("=" * 90)
    header = f"{'ดัชนีชี้วัด (Metric)':<32} | {b_name:<16} | {c_name:<16} | {'ส่วนต่าง (Delta Δ)':<18}"
    print(header)
    print("-" * 90)

    score_delta_str = f"{'+' if agg['delta']['score_delta'] >= 0 else ''}{agg['delta']['score_delta']:.2f} pts"
    print(f"{'คะแนนคุณภาพเฉลี่ย (Quality Score)':<32} | {agg['baseline']['avg_quality_score']:<16.2f} | {agg['candidate']['avg_quality_score']:<16.2f} | {score_delta_str:<18}")

    time_delta_str = f"{agg['delta']['latency_delta_sec']:+.3f}s ({agg['delta']['speedup_ratio']:.2f}x speedup)"
    print(f"{'เวลาหน่วงเฉลี่ย (Latency)':<32} | {agg['baseline']['avg_total_latency_sec']:<16.3f}s | {agg['candidate']['avg_total_latency_sec']:<16.3f}s | {time_delta_str:<18}")

    hr_delta_str = f"{agg['delta']['hit_rate_delta_pct']:+.1f}%"
    print(f"{'อัตราค้นพบเอกสาร (Hit Rate@N)':<32} | {agg['baseline']['hit_rate_pct']:<15.1f}% | {agg['candidate']['hit_rate_pct']:<15.1f}% | {hr_delta_str:<18}")

    rec_delta_str = f"{agg['delta']['recall_delta_pct']:+.1f}%"
    print(f"{'การครอบคลุมคำสำคัญ (Keyword Recall)':<32} | {agg['baseline']['key_phrase_recall_pct']:<15.1f}% | {agg['candidate']['key_phrase_recall_pct']:<15.1f}% | {rec_delta_str:<18}")

    speed_delta = round(agg['candidate']['gen_speed_tps'] - agg['baseline']['gen_speed_tps'], 1)
    speed_delta_str = f"{speed_delta:+.1f} tps"
    print(f"{'ความเร็วสร้างคำตอบ (Throughput)':<32} | {agg['baseline']['gen_speed_tps']:<12.1f} tps | {agg['candidate']['gen_speed_tps']:<12.1f} tps | {speed_delta_str:<18}")

    print("=" * 90)

    print("\n" + "=" * 90)
    print("📋 [ผลทดสอบจำแนกรายข้อ (Per-Question Breakdown)]")
    print("=" * 90)
    print(f"{'ID':<6} | {'หมวดหมู่':<20} | {'Base Score':<11} | {'Cand Score':<11} | {'Δ Score':<9} | {'Base Time':<10} | {'Cand Time':<10}")
    print("-" * 90)
    for c in report["comparisons"]:
        d = c["delta"]
        b = c["baseline"]
        k = c["candidate"]
        delta_str = f"{d['score']:+.1f}"
        print(f"{c['test_id']:<6} | {c['category'][:19]:<20} | {b['quality_score']:<11.1f} | {k['quality_score']:<11.1f} | {delta_str:<9} | {b['timing']['total_seconds']:<9.3f}s | {k['timing']['total_seconds']:<9.3f}s")
    print("=" * 90)


def export_benchmark_report(report: dict[str, Any], output_dir: str = RESULTS_DIR) -> tuple[str, str]:
    """Export the benchmark report to both Markdown and JSON files for Thesis Chapter 4."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b_name = report["baseline_config"]["profile_name"]
    c_name = report["candidate_config"]["profile_name"]

    base_filename = f"config_benchmark_{b_name}_vs_{c_name}_{ts}"
    json_path = os.path.join(output_dir, f"{base_filename}.json")
    md_path = os.path.join(output_dir, f"{base_filename}.md")

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Format Markdown for Chapter 4 Thesis
    agg = report["aggregates"]
    md_content = f"""# 📊 รายงานผลการประเมินการตั้งค่า RAG และการศึกษาผลเชิงประจักษ์ (RAG Configuration & Ablation Study)
**วันที่ประเมินผล:** {report['timestamp']}  
**เอกสารประกอบ:** วิทยานิพนธ์บทที่ 4 (Chapter 4: Results & Evaluation)

---

## 1. การกำหนดค่าระบบที่นำมาเปรียบเทียบ (Configuration Profiles)

| คุณสมบัติ (Hyperparameter) | Baseline: `{b_name}` | Candidate: `{c_name}` |
|---|---|---|
| **คำอธิบาย** | {report['baseline_config'].get('description', '-')} | {report['candidate_config'].get('description', '-')} |
| **LLM Provider / Model** | `{report['baseline_config'].get('llm_provider')}` / `{report['baseline_config'].get('llm_model')}` | `{report['candidate_config'].get('llm_provider')}` / `{report['candidate_config'].get('llm_model')}` |
| **Retrieval Top-K** | {report['baseline_config'].get('top_k')} | {report['candidate_config'].get('top_k')} |
| **Rerank Top-N** | {report['baseline_config'].get('rerank_top_n')} | {report['candidate_config'].get('rerank_top_n')} |
| **Hybrid Search (BM25 + Dense)** | {'เปิดใช้งาน (Enabled)' if report['baseline_config'].get('enable_hybrid') else 'ปิด (Dense Only)'} | {'เปิดใช้งาน (Enabled)' if report['candidate_config'].get('enable_hybrid') else 'ปิด (Dense Only)'} |
| **Neural Re-ranking (Cross-Encoder)** | {'เปิดใช้งาน (Enabled)' if report['baseline_config'].get('enable_reranker') else 'ปิด (Bypassed)'} | {'เปิดใช้งาน (Enabled)' if report['candidate_config'].get('enable_reranker') else 'ปิด (Bypassed)'} |
| **Boilerplate Suppression Filter** | {'เปิดใช้งาน (Enabled)' if report['baseline_config'].get('enable_boilerplate_filter') else 'ปิด (Unfiltered)'} | {'เปิดใช้งาน (Enabled)' if report['candidate_config'].get('enable_boilerplate_filter') else 'ปิด (Unfiltered)'} |
| **Max Context Chunks** | {report['baseline_config'].get('max_context_chunks')} | {report['candidate_config'].get('max_context_chunks')} |
| **Prompt Style Preset** | `{report['baseline_config'].get('prompt_preset')}` | `{report['candidate_config'].get('prompt_preset')}` |
| **Max Predict Tokens** | {report['baseline_config'].get('num_predict')} | {report['candidate_config'].get('num_predict')} |

---

## 2. ตารางสรุปภาพรวมเปรียบเทียบดัชนีชี้วัด (Evaluation Overview & Delta Analysis)

| ดัชนีชี้วัดหลัก (Key Metric) | Baseline (`{b_name}`) | Candidate (`{c_name}`) | ส่วนต่าง (Delta $\\Delta$) |
|---|---|---|---|
| **คะแนนคุณภาพเฉลี่ย (Quality Score)** | **{agg['baseline']['avg_quality_score']:.2f} / 100** | **{agg['candidate']['avg_quality_score']:.2f} / 100** | **{agg['delta']['score_delta']:+.2f} pts** |
| **เวลาหน่วงการตอบสนองเฉลี่ย (Total Latency)** | {agg['baseline']['avg_total_latency_sec']:.3f} s | {agg['candidate']['avg_total_latency_sec']:.3f} s | **{agg['delta']['latency_delta_sec']:+.3f} s ({agg['delta']['speedup_ratio']:.2f}x)** |
| **อัตราการค้นพบเอกสารถูกต้อง (Hit Rate@N)** | {agg['baseline']['hit_rate_pct']:.1f}% | {agg['candidate']['hit_rate_pct']:.1f}% | {agg['delta']['hit_rate_delta_pct']:+.1f}% |
| **ความครอบคลุมข้อเท็จจริง (Keyword Recall)** | {agg['baseline']['key_phrase_recall_pct']:.1f}% | {agg['candidate']['key_phrase_recall_pct']:.1f}% | {agg['delta']['recall_delta_pct']:+.1f}% |
| **ความเร็วสร้างโทเคน (Generation Speed)** | {agg['baseline']['gen_speed_tps']:.1f} TPS | {agg['candidate']['gen_speed_tps']:.1f} TPS | {agg['candidate']['gen_speed_tps'] - agg['baseline']['gen_speed_tps']:+.1f} TPS |

---

## 3. รายละเอียดผลทดสอบจำแนกรายข้อ (Per-Test Granular Results)

| รหัสข้อ | หมวดหมู่ | คำถามทดสอบ (Query) | Base Score | Cand Score | $\\Delta$ Score | Base Time | Cand Time |
|---|---|---|---|---|---|---|---|
"""
    for c in report["comparisons"]:
        d = c["delta"]
        b = c["baseline"]
        k = c["candidate"]
        md_content += f"| `{c['test_id']}` | {c['category']} | \"{c['query']}\" | {b['quality_score']:.1f} | {k['quality_score']:.1f} | **{d['score']:+.1f}** | {b['timing']['total_seconds']:.3f}s | {k['timing']['total_seconds']:.3f}s |\n"

    md_content += """
---

## 4. ข้อสังเกตและการวิเคราะห์ผล (Analytical Discussion)

1. **ผลกระทบต่อคุณภาพคำตอบ (Answer Quality Impact):**
   - การเปลี่ยนแปลงคอนฟิกส่งผลให้คะแนนเฉลี่ยเปลี่ยนไป **""" + f"{agg['delta']['score_delta']:+.2f}" + """ คะแนน**
2. **ประสิทธิภาพด้านเวลาและการประมวลผล (Latency & Throughput Trade-off):**
   - อัตราส่วนความเร็วในการทำงาน (Speedup Ratio): **""" + f"{agg['delta']['speedup_ratio']:.2f}x" + """**
3. **การนำไปอ้างอิงในบทที่ 4:**
   - ข้อมูลนี้สามารถนำไปเขียนเป็นตารางการวิเคราะห์ความไวของพารามิเตอร์ (Sensitivity Analysis) และการศึกษาการตัดทอนโมดูล (Ablation Study) ได้ทันที
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n📁 บันทึกผลการทดสอบเรียบร้อยแล้ว:")
    print(f"  • Markdown Report: {md_path}")
    print(f"  • Raw JSON Data  : {json_path}")
    return md_path, json_path


# =========================================================================
# Interactive Console Menu
# =========================================================================

def interactive_menu() -> None:
    """Interactive CLI Console for configuration and LLM model benchmarking."""
    all_tests = load_golden_dataset()

    while True:
        active_cfg = get_active_config()
        active_prov, active_mod = get_active_llm()

        print("\n" + "=" * 80)
        print("🛠️   RAGcoon Hyperparameter & LLM Benchmark Console (Thesis Chapter 4)")
        print("=" * 80)
        print(f"• คอนฟิก RAG ปัจจุบัน : [{active_cfg.profile_name}] Top-K={active_cfg.top_k}, Top-N={active_cfg.rerank_top_n}, Hybrid={active_cfg.enable_hybrid}, Prompt={active_cfg.prompt_preset}")
        print(f"• LLM ปัจจุบัน        : {active_prov.upper()} ({active_mod})")
        print("-" * 80)
        print("เลือกประเภทการทดลอง:")
        print("  [1] การศึกษาการตัดทอนโมดูล (Ablation Study Suite):")
        print("      - Baseline vs Dense Only (ไม่มี Sparse BM25)")
        print("      - Baseline vs No Reranker (ไม่มี Neural Cross-Encoder)")
        print("      - Baseline vs No Boilerplate Filter (ไม่กรองขยะ)")
        print("  [2] การเปรียบเทียบ Hyperparameter Presets (Sensitivity Analysis):")
        print("      - Baseline (precision_hybrid) vs Fast-Mode (Speed-Optimized)")
        print("      - Baseline (precision_hybrid) vs Deep-Academic (Comprehensive)")
        print("  [3] การเปรียบเทียบสมรรถนะของแต่ละโมเดลภาษา (Multi-LLM Benchmark):")
        print("      - Ollama Gemma 3 (4B) vs Ollama Qwen 3 (4B) vs Google Gemini vs ChatGPT")
        print("  [4] ทดสอบแบบเจาะลึก 1 ข้อ (Single Ground Truth Inspection)")
        print("  [5] รันการทดสอบ Golden Dataset ทั้งหมด 15 ข้อ และส่งออกรายงานบทที่ 4")
        print("  [6] ปรับแต่งคอนฟิกแบบกำหนดเอง (Custom Hyperparameter Tuning)")
        print("  [Q] กลับสู่เมนูหลัก")
        print("=" * 80)

        choice = input("\n👉 กรุณาเลือกตัวเลือก (1-6, Q): ").strip().upper()
        if choice == "Q":
            print("\n👋 ขอบคุณครับ\n")
            break

        elif choice == "1":
            print("\nเลือกรูปแบบการทดลองตัดทอน (Ablation Study):")
            print("  [A] Baseline vs Dense Only (Ablation 1: วัดผลของ BM25 Hybrid)")
            print("  [B] Baseline vs No Reranker (Ablation 2: วัดผลของ Neural Reranking)")
            print("  [C] Baseline vs No Filter (Ablation 3: วัดผลของการกรองขยะ Boilerplate)")
            sub = input("เลือกตัวเลือก (A, B, C): ").strip().upper()
            base = get_config_preset("precision_hybrid")
            cand_map = {
                "A": "ablation_dense_only",
                "B": "ablation_no_rerank",
                "C": "ablation_no_filter",
            }
            cand_id = cand_map.get(sub, "ablation_dense_only")
            cand = get_config_preset(cand_id)
            # Run quick subset or all
            rep = run_comparative_benchmark(base, cand, all_tests[:5])
            export_benchmark_report(rep)

        elif choice == "2":
            print("\nเลือกโหมดที่ต้องการเปรียบเทียบกับ Baseline:")
            print("  [F] Baseline vs Fast-Mode (เน้นความเร็ว Latency)")
            print("  [D] Baseline vs Deep-Academic (เน้นความลึกและครอบคลุม)")
            sub = input("เลือกตัวเลือก (F, D): ").strip().upper()
            base = get_config_preset("precision_hybrid")
            cand_id = "fast_mode" if sub == "F" else "deep_academic"
            cand = get_config_preset(cand_id)
            rep = run_comparative_benchmark(base, cand, all_tests[:5])
            export_benchmark_report(rep)

        elif choice == "3":
            print("\n🤖 [เปรียบเทียบสมรรถนะของโมเดลภาษา (Multi-LLM)]")
            print("โมเดลที่มีในระบบ:")
            for idx, p in enumerate(AVAILABLE_LLM_PROFILES, start=1):
                print(f"  [{idx}] {p['label']} ({p['provider']}/{p['model']})")
            
            print("\nเลือกคำถามทดสอบ:")
            print("  [1] \"โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง\" (Sparse / Exact Code)")
            print("  [2] \"เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device\" (Comparison)")
            print("  [3] \"อาจารสุรพลดูแลเรื่องไรบ้าง\" (Advisor Lookup)")
            print("  [4] พิมพ์คำถามทดสอบเอง")
            q_choice = input("เลือกหมายเลขคำถาม (1-4): ").strip()
            if q_choice == "1":
                q_text = "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง"
            elif q_choice == "2":
                q_text = "เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device"
            elif q_choice == "3":
                q_text = "อาจารสุรพลดูแลเรื่องไรบ้าง"
            else:
                q_text = input("พิมพ์คำถาม: ").strip() or "ขั้นตอนการทำงานของ The LoRaWAN"

            from backend.app.rag.evaluation.compare_llms import run_llm_comparison
            run_llm_comparison(q_text)

        elif choice == "4":
            print("\nรายการคำถามทดสอบมาตรฐาน (Golden Dataset):")
            for idx, tc in enumerate(all_tests, start=1):
                print(f"  [{idx}] {tc['id']} ({tc['category']}): \"{tc['query']}\"")
            sub = input(f"เลือกหมายเลขข้อ (1-{len(all_tests)}): ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(all_tests):
                tc = all_tests[int(sub) - 1]
                base = get_config_preset("precision_hybrid")
                cand = get_config_preset("fast_mode")
                rep = run_comparative_benchmark(base, cand, [tc])
                export_benchmark_report(rep)

        elif choice == "5":
            print("\n🚀 กำลังประเมินผลเต็มรูปแบบครบทั้ง 15 ข้อใน Golden Dataset...")
            base = get_config_preset("precision_hybrid")
            cand = get_config_preset("fast_mode")
            rep = run_comparative_benchmark(base, cand, all_tests)
            export_benchmark_report(rep)

        elif choice == "6":
            print("\n🔧 [ปรับแต่งค่า Hyperparameter ด้วยตนเอง]")
            top_k_str = input(f"Top-K สำหรับการค้นหา (ปัจจุบัน: {active_cfg.top_k}): ").strip()
            top_n_str = input(f"Top-N สำหรับ Rerank (ปัจจุบัน: {active_cfg.rerank_top_n}): ").strip()
            chunk_str = input(f"จำนวน Chunk สูงสุดเข้า LLM (ปัจจุบัน: {active_cfg.max_context_chunks}): ").strip()
            prov_str = input(f"LLM Provider [ollama/gemini/openai] (ปัจจุบัน: {active_cfg.llm_provider}): ").strip()
            mod_str = input(f"LLM Model (ปัจจุบัน: {active_cfg.llm_model}): ").strip()
            style_str = input(f"Prompt Preset [concise/balanced/deep_academic] (ปัจจุบัน: {active_cfg.prompt_preset}): ").strip()

            new_cfg = active_cfg.clone()
            if top_k_str.isdigit():
                new_cfg.top_k = int(top_k_str)
            if top_n_str.isdigit():
                new_cfg.rerank_top_n = int(top_n_str)
            if chunk_str.isdigit():
                new_cfg.max_context_chunks = int(chunk_str)
            if prov_str:
                new_cfg.llm_provider = prov_str.lower()
            if mod_str:
                new_cfg.llm_model = mod_str
            if style_str in {"concise", "balanced", "deep_academic"}:
                new_cfg.prompt_preset = style_str

            new_cfg.profile_name = "user_tuned"
            new_cfg.description = "User manually configured parameters"
            set_active_config(new_cfg)
            print(f"\n✅ อัปเดตและเปิดใช้งานคอนฟิกเรียบร้อยแล้ว: {new_cfg.to_dict()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGcoon Hyperparameter Benchmark Engine")
    parser.add_argument("--baseline", type=str, default="precision_hybrid", help="Baseline config preset name")
    parser.add_argument("--candidate", type=str, default="fast_mode", help="Candidate config preset name")
    parser.add_argument("--test-id", type=str, default=None, help="Specific test case ID(s) separated by comma")
    parser.add_argument("--all", action="store_true", help="Run benchmark across all 15 golden test cases")
    parser.add_argument("--models", type=str, default=None, help="Run multi-LLM benchmark across specified models")

    args = parser.parse_args()

    if args.models:
        from backend.app.rag.evaluation.compare_llms import run_llm_comparison
        q = "เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device"
        run_llm_comparison(q)
        return

    if args.all or args.test_id:
        all_tests = load_golden_dataset()
        if args.test_id:
            ids = [i.strip().upper() for i in args.test_id.split(",")]
            selected_tests = [t for t in all_tests if t["id"].upper() in ids]
        else:
            selected_tests = all_tests

        base_cfg = get_config_preset(args.baseline)
        cand_cfg = get_config_preset(args.candidate)

        rep = run_comparative_benchmark(base_cfg, cand_cfg, selected_tests)
        export_benchmark_report(rep)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
