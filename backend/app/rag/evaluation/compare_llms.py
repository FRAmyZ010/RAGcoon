"""
Module: compare_llms.py
Description:
    RAGcoon Multi-LLM Benchmark & Comparative Evaluation Engine.
    Executes and benchmarks RAG queries across multiple LLM backends:
      1. Ollama Gemma 3 (4B) [Local Default]
      2. Ollama Qwen 3 (4B) [Local Reasoning]
      3. Google Gemini 3.5 Flash [Cloud High-Speed]
      4. OpenAI ChatGPT (GPT-4o Mini) [Cloud SOTA]

Usage:
    python backend/app/rag/evaluation/compare_llms.py
    python backend/app/rag/evaluation/compare_llms.py --query "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง"
    python backend/app/rag/evaluation/compare_llms.py --models gemma3,gemini
"""

import sys
import os
import io
import time
import argparse
from typing import Any, Optional

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.rag.retrieval.llm_provider import (
    AVAILABLE_LLM_PROFILES,
    get_llm_provider,
    set_active_llm,
    get_active_llm,
)
from backend.app.rag.retrieval.prompt import answer_question
from backend.app.rag.evaluation.compare_pipelines import evaluate_output_quality

BENCHMARK_PROMPT_PRESETS = [
    {
        "id": 1,
        "category": "ฮาร์ดแวร์เฉพาะทาง (Sparse / Exact Code)",
        "query": "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",
        "description": "ทดสอบการสังเคราะห์รายชื่อโครงงานและดึงหลักฐานเกี่ยวกับโมดูล LoRa SX1276",
    },
    {
        "id": 2,
        "category": "ภาพรวมและโครงสร้างระบบ (Deep Dive / Overview)",
        "query": "ขั้นตอนการทำงานและการทดลองของ The LoRaWAN",
        "description": "ทดสอบการแจกแจงโครงสร้างสถาปัตยกรรม วิธีการทดลอง และการจัดหัวข้อ Markdown",
    },
    {
        "id": 3,
        "category": "การค้นหาข้อมูลบุคคล (Advisors & Metadata)",
        "query": "อาจารสุรพลดูแลเรื่องไรบ้าง",
        "description": "ทดสอบการประมวลผลคำถามชื่ออาจารย์ที่สะกดผิดและการสรุปโครงงานที่กำกับดูแล",
    },
    {
        "id": 4,
        "category": "การเปรียบเทียบเชิงวิเคราะห์ (Comparison)",
        "query": "เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device",
        "description": "ทดสอบความสามารถในการสร้างตารางเปรียบเทียบ Markdown แยกคอลัมน์ชัดเจน",
    },
    {
        "id": 5,
        "category": "การแนะนำโครงงานตามโจทย์ (Recommendation)",
        "query": "แนะนำโครงงานสำหรับตรวจวัดสภาพแวดล้อมหรือการเกษตรอัจฉริยะ",
        "description": "ทดสอบการจัดกลุ่มแนะนำ พร้อมระบุเอกสารอ้างอิงและข้อเสนอแนะ AI",
    },
]


def _print_box_header(title: str, width: int = 90, char: str = "=") -> None:
    print("\n" + char * width)
    print(f" {title}")
    print(char * width)


def benchmark_single_model(
    profile: dict[str, Any], query: str
) -> dict[str, Any]:
    """Execute a query against a specific LLM profile and record granular benchmark metrics."""
    provider_name = profile["provider"]
    model_name = profile["model"]
    label = profile["label"]

    t0 = time.perf_counter()
    try:
        res = answer_question(
            query,
            llm_provider=provider_name,
            llm_model=model_name,
        )
        total_time = time.perf_counter() - t0
        answer = res.get("answer", "")
        perf = res.get("performance", {})
        timing = res.get("timing", {})
        llm_time = timing.get("llm_seconds", 0.0) or perf.get("llm_seconds", total_time)
        citations = res.get("citations", [])

        # Quality scoring
        quality_eval = evaluate_output_quality(
            answer=answer,
            latency_sec=total_time,
            retrieved_count=res.get("retrieved_count", 0),
            sources=res.get("sources", []),
            has_fast_path=bool(res.get("fast_path_used")),
        )

        is_error = "⚠️" in answer and ("error" in answer.lower() or "failed" in answer.lower() or "quota" in answer.lower())

        return {
            "profile_id": profile["id"],
            "label": label,
            "provider": provider_name,
            "model": model_name,
            "is_cloud": profile.get("is_cloud", False),
            "success": not is_error,
            "total_latency_sec": round(total_time, 3),
            "llm_latency_sec": round(llm_time, 3),
            "ttft_sec": round(perf.get("ttft_seconds", llm_time), 3),
            "tokens_per_sec": round(perf.get("gen_speed_tps", 0.0), 1),
            "input_tokens": perf.get("input_tokens", 0),
            "output_tokens": perf.get("output_tokens", 0),
            "citations_count": len(citations),
            "quality_score": quality_eval["total_score"],
            "score_breakdown": quality_eval["breakdown"],
            "answer": answer,
            "error": answer if is_error else None,
        }
    except Exception as exc:
        total_time = time.perf_counter() - t0
        return {
            "profile_id": profile["id"],
            "label": label,
            "provider": provider_name,
            "model": model_name,
            "is_cloud": profile.get("is_cloud", False),
            "success": False,
            "total_latency_sec": round(total_time, 3),
            "llm_latency_sec": round(total_time, 3),
            "ttft_sec": 0.0,
            "tokens_per_sec": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "citations_count": 0,
            "quality_score": 0.0,
            "score_breakdown": {},
            "answer": f"⚠️ Exception: {exc}",
            "error": str(exc),
        }


def run_llm_comparison(
    query: str, selected_profiles: Optional[list[dict[str, Any]]] = None
) -> list[dict[str, Any]]:
    """Run benchmark comparison across all or selected LLM profiles."""
    profiles = selected_profiles or AVAILABLE_LLM_PROFILES

    _print_box_header(f"🧪 RAGcoon Multi-LLM Benchmark Runner")
    print(f"• คำถามทดสอบ (Query): \"{query}\"")
    print(f"• จำนวนโมเดลที่เปรียบเทียบ: {len(profiles)} โมเดล")
    print("-" * 90)

    results = []
    for idx, p in enumerate(profiles, start=1):
        print(f"\n[{idx}/{len(profiles)}] ⏳ กำลังทดสอบ: {p['label']} ...")
        t_start = time.perf_counter()
        res = benchmark_single_model(p, query)
        dur = time.perf_counter() - t_start

        if res["success"]:
            print(f"      ✅ สำเร็จใน {res['total_latency_sec']}s | ความเร็ว: {res['tokens_per_sec']} TPS | คะแนน: {res['quality_score']}/100")
        else:
            print(f"      ⚠️ แจ้งเตือน: {res['error'][:90]}...")

        results.append(res)

    print("\n" + "=" * 90)
    print("📊 [ตารางเปรียบเทียบผลการทดสอบ LLM แต่ละโมเดล (Side-by-Side Comparison)]")
    print("=" * 90)
    print(f"{'โมเดล (Model)':<36} | {'เวลา (Total)':<11} | {'ความเร็ว':<10} | {'Tokens In/Out':<13} | {'คะแนน':<7} | {'สถานะ':<8}")
    print("-" * 90)

    for r in results:
        status = "✅ สำเร็จ" if r["success"] else "⚠️ ผิดพลาด"
        tokens_str = f"{r['input_tokens']}/{r['output_tokens']}"
        speed_str = f"{r['tokens_per_sec']} tps" if r['tokens_per_sec'] > 0 else "-"
        time_str = f"{r['total_latency_sec']}s"
        score_str = f"{r['quality_score']:.1f}" if r["success"] else "0.0"
        print(f"{r['label'][:35]:<36} | {time_str:<11} | {speed_str:<10} | {tokens_str:<13} | {score_str:<7} | {status:<8}")

    print("-" * 90)

    # Detailed Snippets
    print("\n" + "=" * 90)
    print("📝 [ตัวอย่างคำตอบที่สร้างโดยแต่ละโมเดล (Generated Responses Preview)]")
    print("=" * 90)
    for r in results:
        print(f"\n--- 🤖 [{r['label']}] ---")
        if r["success"]:
            cleaned_snippet = r["answer"].strip()
            # Indent output nicely
            lines = cleaned_snippet.split("\n")
            preview = "\n".join(lines[:8])
            if len(lines) > 8:
                preview += f"\n... [แสดงย่อ {len(lines)} บรรทัด]"
            print(preview)
        else:
            print(f"⚠️ ข้อผิดพลาด: {r['error']}")

    print("\n" + "=" * 90)
    return results


def interactive_llm_menu() -> None:
    """Interactive CLI menu for LLM benchmark testing & switching."""
    while True:
        active_prov, active_mod = get_active_llm()
        print("\n" + "=" * 80)
        print("🤖   RAGcoon Multi-LLM Benchmark & Selection Console")
        print("=" * 80)
        print(f"• 🌟 โมเดลปัจจุบันที่ระบบเปิดใช้งาน: {active_prov.upper()} ({active_mod})")
        print("-" * 80)
        print("เลือกการดำเนินการ:")
        print("  [1] เปรียบเทียบโมเดลทั้งหมด ด้วยคำถามทดสอบมาตรฐาน (Presets 1-5)")
        print("  [2] พิมพ์คำถามเอง เพื่อเปรียบเทียบทุกโมเดล (Custom Query Benchmark)")
        print("  [3] สลับโมเดลที่ใช้งานหลักในระบบ (Switch Active LLM)")
        print("  [4] ตรวจสอบการเชื่อมต่อและความพร้อมของทุกโมเดล (Ping / Health Check)")
        print("  [Q] ออกจากเมนู")
        print("=" * 80)

        choice = input("\n👉 กรุณาเลือกเมนู (1-4, Q): ").strip().upper()
        if choice == "Q":
            print("\n👋 ขอบคุณครับ\n")
            break
        elif choice == "1":
            print("\nเลือกโจทย์ทดสอบมาตรฐาน:")
            for p in BENCHMARK_PROMPT_PRESETS:
                print(f"  [{p['id']}] {p['category']}: \"{p['query']}\"")
            sub = input(f"\nเลือกหมายเลขข้อ (1-{len(BENCHMARK_PROMPT_PRESETS)}): ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(BENCHMARK_PROMPT_PRESETS):
                preset = BENCHMARK_PROMPT_PRESETS[int(sub) - 1]
                run_llm_comparison(preset["query"])
            else:
                print("⚠️ ตัวเลือกไม่ถูกต้อง")
        elif choice == "2":
            custom_q = input("\n📝 พิมพ์คำถามภาษาธรรมชาติที่ต้องการทดสอบ: ").strip()
            if custom_q:
                run_llm_comparison(custom_q)
        elif choice == "3":
            print("\nเลือกรุ่นโมเดลที่ต้องการตั้งเป็นค่าเริ่มต้น:")
            for idx, p in enumerate(AVAILABLE_LLM_PROFILES, start=1):
                cur_marker = " (Active 🌟)" if p["provider"] == active_prov and p["model"] == active_mod else ""
                print(f"  [{idx}] {p['label']}{cur_marker}")
                print(f"      • {p['description']}")
            sub = input(f"\nเลือกโมเดล (1-{len(AVAILABLE_LLM_PROFILES)}): ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(AVAILABLE_LLM_PROFILES):
                target = AVAILABLE_LLM_PROFILES[int(sub) - 1]
                set_active_llm(target["provider"], target["model"])
                print(f"\n✅ ตั้งค่าสำเร็จ: ระบบจะใช้ '{target['label']}' เป็นค่าเริ่มต้นสำหรับทุกการค้นหา")
            else:
                print("⚠️ ตัวเลือกไม่ถูกต้อง")
        elif choice == "4":
            print("\n⏳ กำลังทดสอบ Health Check ทุกโมเดล...")
            from backend.app.rag.retrieval.llm_provider import test_provider_connectivity
            for p in AVAILABLE_LLM_PROFILES:
                res = test_provider_connectivity(p["provider"], p["model"])
                status = "✅ CONNECTED" if res["success"] else "⚠️ ERROR / NOTICE"
                print(f"  • {p['label']:<40} : {status} (Latency: {res['latency_sec']}s)")
                if not res["success"]:
                    print(f"    └─ ข้อความ: {res['response_sample'][:100]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGcoon Multi-LLM Benchmark & Comparative Engine")
    parser.add_argument("--query", "-q", type=str, help="Question to run across models", default=None)
    parser.add_argument("--models", "-m", type=str, help="Comma-separated model IDs or providers to include", default=None)
    parser.add_argument("--preset", "-p", type=int, help="Preset query ID (1-5)", default=None)

    args = parser.parse_args()

    selected_profiles = None
    if args.models:
        filter_keys = [k.strip().lower() for k in args.models.split(",")]
        selected_profiles = [
            p for p in AVAILABLE_LLM_PROFILES
            if any(k in p["id"].lower() or k in p["provider"].lower() or k in p["model"].lower() for k in filter_keys)
        ]
        if not selected_profiles:
            print(f"⚠️ ไม่พบโมเดลที่ตรงกับ '{args.models}'")
            return

    if args.query:
        run_llm_comparison(args.query, selected_profiles=selected_profiles)
    elif args.preset is not None:
        if 1 <= args.preset <= len(BENCHMARK_PROMPT_PRESETS):
            q = BENCHMARK_PROMPT_PRESETS[args.preset - 1]["query"]
            run_llm_comparison(q, selected_profiles=selected_profiles)
        else:
            print(f"⚠️ Preset ต้องอยู่ระหว่าง 1 ถึง {len(BENCHMARK_PROMPT_PRESETS)}")
    else:
        interactive_llm_menu()


if __name__ == "__main__":
    main()
