"""
Module: evaluate_retrieval.py
Description:
    Academic Retrieval Benchmark Evaluation Suite for Chapter 4 (System Evaluation).
    - Compares:
        1. Dense Vector Only (Multilingual-E5-base)
        2. BM25 Sparse Only (BM25Okapi with technical tokenization)
        3. True Hybrid Search (Dense + BM25 with RRF)
        4. True Hybrid Search + Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)
    - Computes:
        * Precision@K (K=1, 3, 5, 10)
        * Recall@K (K=1, 3, 5, 10)
        * MRR (Mean Reciprocal Rank)
        * Hit Rate@K (Success Rate)
        * Retrieval Latency (ms)
    - Generates multi-sheet Excel report and publication-ready visualization charts.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.rag.retrieval.bm25 import bm25_engine
from backend.app.rag.retrieval.hybrid import hybrid_search
from backend.app.rag.retrieval.rerank import rerank
from backend.app.rag.retrieval.semantic import semantic_search


DEFAULT_GROUND_TRUTH_QUERIES = [
    # Category 1: Exact Hardware & Technical Models
    {
        "query_id": 1,
        "category": "Exact Technical Models",
        "query": "Arduino Mega 2560",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 2,
        "category": "Exact Technical Models",
        "query": "Analog pH sensor PE HOSE",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 3,
        "category": "Exact Technical Models",
        "query": "Electrical Conductive Sensor EC sensor",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 4,
        "category": "Exact Technical Models",
        "query": "Bluetooth Low Energy BLE Cisco WLAN",
        "relevant_titles": ["THE DEVELOPMENT OF BLUETOOTH LOW ENERGY IN CISCO WLAN"],
        "relevant_sources": ["SENIOR-THE-DEVELOPMENT-OF-BLUETOOTH-LOW-ENERGY-IN-CISCO-WLAN.pdf"],
    },
    {
        "query_id": 5,
        "category": "Exact Technical Models",
        "query": "Aironet Access Point AP power saving",
        "relevant_titles": ["THE DEVELOPMENT OF BLUETOOTH LOW ENERGY IN CISCO WLAN"],
        "relevant_sources": ["SENIOR-THE-DEVELOPMENT-OF-BLUETOOTH-LOW-ENERGY-IN-CISCO-WLAN.pdf"],
    },
    {
        "query_id": 6,
        "category": "Exact Technical Models",
        "query": "snubber circuit surge suppressor diode opto-isolated relay",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },

    # Category 2: Project Titles & Academic Identifiers
    {
        "query_id": 7,
        "category": "Titles & Identifiers",
        "query": "INTELLIGENT WATERING SYSTEM",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 8,
        "category": "Titles & Identifiers",
        "query": "QUALITY DISCHARGE PLANNING PROJECT",
        "relevant_titles": ["QUALITY DISCHARGE PLANNING PROJECT"],
        "relevant_sources": ["QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"],
    },
    {
        "query_id": 9,
        "category": "Titles & Identifiers",
        "query": "3D WALLPAPER STOCK MANAGEMENT SYSTEM",
        "relevant_titles": ["3D WALLPAPER STOCK MANAGEMENT SYSTEM"],
        "relevant_sources": ["Proposal Document.docx.pdf"],
    },
    {
        "query_id": 10,
        "category": "Titles & Identifiers",
        "query": "ONLINE MFU-LECTURER APPOINTMENT SYSTEM",
        "relevant_titles": ["ONLINE MFU-LECTURER APPOINTMENT SYSTEM"],
        "relevant_sources": ["COMPUTER ENGINEERING  ONLINE MFU LECTURER  APPOINTMENT SYSTEM.pdf"],
    },
    {
        "query_id": 11,
        "category": "Titles & Identifiers",
        "query": "Gem car tracking application",
        "relevant_titles": ["Gem car tracking application"],
        "relevant_sources": ["Pre-Project_Gem_Car2_edit2_V2.pdf"],
    },
    {
        "query_id": 12,
        "category": "Titles & Identifiers",
        "query": "Cisco Mobility Express controller",
        "relevant_titles": ["THE DEVELOPMENT OF BLUETOOTH LOW ENERGY IN CISCO WLAN"],
        "relevant_sources": ["SENIOR-THE-DEVELOPMENT-OF-BLUETOOTH-LOW-ENERGY-IN-CISCO-WLAN.pdf"],
    },

    # Category 3: Code, SQL & Technical Implementations
    {
        "query_id": 13,
        "category": "Code & Technical Implementation",
        "query": "pH adjustment system automatic mixing system NPK",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 14,
        "category": "Code & Technical Implementation",
        "query": "Modbus 4-20mA analog signal to digital",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 15,
        "category": "Code & Technical Implementation",
        "query": "Bootstrap Twitter open-source frontend framework",
        "relevant_titles": ["ONLINE MFU-LECTURER APPOINTMENT SYSTEM"],
        "relevant_sources": ["COMPUTER ENGINEERING  ONLINE MFU LECTURER  APPOINTMENT SYSTEM.pdf"],
    },
    {
        "query_id": 16,
        "category": "Code & Technical Implementation",
        "query": "inventory stock deduct sold quantity workflow diagram",
        "relevant_titles": ["3D WALLPAPER STOCK MANAGEMENT SYSTEM"],
        "relevant_sources": ["Proposal Document.docx.pdf"],
    },
    {
        "query_id": 17,
        "category": "Code & Technical Implementation",
        "query": "GPS tracking module vehicle location",
        "relevant_titles": ["Gem car tracking application"],
        "relevant_sources": ["Pre-Project_Gem_Car2_edit2_V2.pdf"],
    },
    {
        "query_id": 18,
        "category": "Code & Technical Implementation",
        "query": "patient discharge statistical data medical plan",
        "relevant_titles": ["QUALITY DISCHARGE PLANNING PROJECT"],
        "relevant_sources": ["QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"],
    },

    # Category 4: Natural Language Semantic Queries (Thai & English)
    {
        "query_id": 19,
        "category": "Semantic Natural Language",
        "query": "ระบบรดน้ำอัตโนมัติสำหรับแปลงผักที่ใช้ขุยมะพร้าวแทนดิน",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 20,
        "category": "Semantic Natural Language",
        "query": "การวางแผนดูแลคนไข้เมื่อต้องออกจากโรงพยาบาล",
        "relevant_titles": ["QUALITY DISCHARGE PLANNING PROJECT"],
        "relevant_sources": ["QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"],
    },
    {
        "query_id": 21,
        "category": "Semantic Natural Language",
        "query": "ระบบนัดหมายอาจารย์มหาวิทยาลัยออนไลน์",
        "relevant_titles": ["ONLINE MFU-LECTURER APPOINTMENT SYSTEM"],
        "relevant_sources": ["COMPUTER ENGINEERING  ONLINE MFU LECTURER  APPOINTMENT SYSTEM.pdf"],
    },
    {
        "query_id": 22,
        "category": "Semantic Natural Language",
        "query": "แอปพลิเคชันสำหรับติดตามตำแหน่งและเส้นทางของรถกอล์ฟ",
        "relevant_titles": ["Gem car tracking application"],
        "relevant_sources": ["Pre-Project_Gem_Car2_edit2_V2.pdf"],
    },
    {
        "query_id": 23,
        "category": "Semantic Natural Language",
        "query": "ระบบจัดการคลังสินค้าและคำนวณยอดขายวอลเปเปอร์ 3 มิติ",
        "relevant_titles": ["3D WALLPAPER STOCK MANAGEMENT SYSTEM"],
        "relevant_sources": ["Proposal Document.docx.pdf"],
    },
    {
        "query_id": 24,
        "category": "Semantic Natural Language",
        "query": "energy saving mechanisms in wireless access points using BLE",
        "relevant_titles": ["THE DEVELOPMENT OF BLUETOOTH LOW ENERGY IN CISCO WLAN"],
        "relevant_sources": ["SENIOR-THE-DEVELOPMENT-OF-BLUETOOTH-LOW-ENERGY-IN-CISCO-WLAN.pdf"],
    },

    # Category 5: Advisors & Authors Metadata
    {
        "query_id": 25,
        "category": "Advisors & Authors Metadata",
        "query": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM", "QUALITY DISCHARGE PLANNING PROJECT"],
        "relevant_sources": ["Final document(8).pdf", "QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"],
    },
    {
        "query_id": 26,
        "category": "Advisors & Authors Metadata",
        "query": "Aj.Dr. Surapol Vorapatratorn",
        "relevant_titles": ["ONLINE MFU-LECTURER APPOINTMENT SYSTEM", "Gem car tracking application", "INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["COMPUTER ENGINEERING  ONLINE MFU LECTURER  APPOINTMENT SYSTEM.pdf", "Pre-Project_Gem_Car2_edit2_V2.pdf", "Final document(8).pdf"],
    },
    {
        "query_id": 27,
        "category": "Advisors & Authors Metadata",
        "query": "Assoc.Prof. Nattapol Aunsri",
        "relevant_titles": ["3D WALLPAPER STOCK MANAGEMENT SYSTEM"],
        "relevant_sources": ["Proposal Document.docx.pdf"],
    },
    {
        "query_id": 28,
        "category": "Advisors & Authors Metadata",
        "query": "Simon Yosboon Tonkla Maneerat",
        "relevant_titles": ["INTELLIGENT WATERING SYSTEM"],
        "relevant_sources": ["Final document(8).pdf"],
    },
    {
        "query_id": 29,
        "category": "Advisors & Authors Metadata",
        "query": "Teerapat Puangkankham Witchapon Proadpranee",
        "relevant_titles": ["QUALITY DISCHARGE PLANNING PROJECT"],
        "relevant_sources": ["QUALITY-DISCHARGE-PLANNING-PROJECT.pdf"],
    },
    {
        "query_id": 30,
        "category": "Advisors & Authors Metadata",
        "query": "Bek Shung Zhen Noraphit Pornjaruskunwathana Supawish Kodyee",
        "relevant_titles": ["3D WALLPAPER STOCK MANAGEMENT SYSTEM"],
        "relevant_sources": ["Proposal Document.docx.pdf"],
    },
]


def is_hit(item: dict[str, Any], relevant_titles: list[str], relevant_sources: list[str]) -> bool:
    """Check if a retrieved item matches any target title or source file."""
    payload = item.get("payload", {}) or {}
    source = str(payload.get("source", "")).strip().lower()
    title = str(payload.get("project_title") or payload.get("title", "")).strip().lower()

    for rel_s in relevant_sources:
        rel_s_low = rel_s.strip().lower()
        if rel_s_low in source or source in rel_s_low:
            return True

    for rel_t in relevant_titles:
        rel_t_low = rel_t.strip().lower()
        if rel_t_low in title or title in rel_t_low or (len(rel_t_low) > 8 and rel_t_low[:15] in title):
            return True

    return False


def evaluate_query_retrieval(
    query_item: dict[str, Any],
    method_name: str,
    top_k: int = 10,
) -> dict[str, Any]:
    """Execute search using the specified method and compute retrieval metrics."""
    q_text = query_item["query"]
    rel_titles = query_item.get("relevant_titles", [])
    rel_sources = query_item.get("relevant_sources", [])

    t0 = time.perf_counter()

    if method_name == "Dense Only":
        results = semantic_search(q_text, top_k=top_k)
    elif method_name == "BM25 Only":
        results = bm25_engine.search(q_text, top_k=top_k)
    elif method_name == "True Hybrid (RRF)":
        results = hybrid_search(q_text, top_k=top_k)
    elif method_name == "True Hybrid + Rerank":
        raw_results = hybrid_search(q_text, top_k=top_k * 2)
        results = rerank(q_text, raw_results, top_n=top_k)
    else:
        raise ValueError(f"Unknown retrieval method: {method_name}")

    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Calculate Hits
    hits = [1 if is_hit(r, rel_titles, rel_sources) else 0 for r in results]

    # Precision & Recall & HitRate at K
    metrics = {
        "Query_ID": query_item["query_id"],
        "Category": query_item["category"],
        "Query": q_text,
        "Method": method_name,
        "Latency_ms": round(latency_ms, 2),
        "Retrieved_Count": len(results),
    }

    # Find first relevant rank for MRR
    first_rank = 0
    for idx, h in enumerate(hits, start=1):
        if h == 1:
            first_rank = idx
            break

    metrics["MRR"] = (1.0 / first_rank) if first_rank > 0 else 0.0
    metrics["First_Hit_Rank"] = first_rank if first_rank > 0 else "-"

    for k in [1, 3, 5, 10]:
        k_hits = sum(hits[:k])
        metrics[f"P@{k}"] = round((k_hits / k) * 100.0, 2)
        metrics[f"Recall@{k}"] = round((k_hits / max(1, len(rel_sources))) * 100.0, 2)
        metrics[f"HitRate@{k}"] = 100.0 if k_hits > 0 else 0.0

    # Top-1 retrieved info
    top_doc = results[0].get("payload", {}).get("source", "None") if results else "None"
    metrics["Top_1_Source"] = top_doc
    metrics["Top_1_Success"] = "PASS" if (hits and hits[0] == 1) else "FAIL"

    return metrics


def run_full_retrieval_benchmark(
    ground_truth: list[dict[str, Any]],
    output_excel: Optional[Path] = None,
    output_chart: Optional[Path] = None,
) -> pd.DataFrame:
    """Run full academic benchmark across all 4 retrieval methods and generate deliverables."""
    methods = [
        "Dense Only",
        "BM25 Only",
        "True Hybrid (RRF)",
        "True Hybrid + Rerank",
    ]

    print("\n" + "=" * 90)
    print("🚀 RUNNING ACADEMIC RETRIEVAL BENCHMARK SUITE (DENSE vs BM25 vs TRUE HYBRID)")
    print(f"📋 Total Evaluation Queries: {len(ground_truth)} | Methods: {len(methods)}")
    print("=" * 90)

    # Make sure BM25 index is preloaded
    bm25_engine.load_index()

    all_records: list[dict[str, Any]] = []

    for m in methods:
        print(f"\n🔄 Testing Method: [{m}] across {len(ground_truth)} queries...")
        for q_item in ground_truth:
            rec = evaluate_query_retrieval(q_item, method_name=m, top_k=10)
            all_records.append(rec)

    df_all = pd.DataFrame(all_records)

    # 1. Summary Comparison Table
    summary_rows = []
    for m in methods:
        sub = df_all[df_all["Method"] == m]
        summary_rows.append({
            "Retrieval Method": m,
            "MRR": round(sub["MRR"].mean(), 4),
            "Hit Rate@1 (%)": round(sub["HitRate@1"].mean(), 2),
            "Hit Rate@3 (%)": round(sub["HitRate@3"].mean(), 2),
            "Hit Rate@5 (%)": round(sub["HitRate@5"].mean(), 2),
            "Hit Rate@10 (%)": round(sub["HitRate@10"].mean(), 2),
            "Precision@1 (%)": round(sub["P@1"].mean(), 2),
            "Precision@3 (%)": round(sub["P@3"].mean(), 2),
            "Precision@5 (%)": round(sub["P@5"].mean(), 2),
            "Recall@1 (%)": round(sub["Recall@1"].mean(), 2),
            "Recall@3 (%)": round(sub["Recall@3"].mean(), 2),
            "Recall@5 (%)": round(sub["Recall@5"].mean(), 2),
            "Recall@10 (%)": round(sub["Recall@10"].mean(), 2),
            "Avg Latency (ms)": round(sub["Latency_ms"].mean(), 2),
        })

    df_summary = pd.DataFrame(summary_rows)

    # 2. Category Breakdown Table
    cat_summary = (
        df_all.groupby(["Category", "Method"])[["MRR", "HitRate@5", "Recall@5", "P@5", "Latency_ms"]]
        .mean()
        .reset_index()
    )
    cat_summary["MRR"] = cat_summary["MRR"].round(4)
    cat_summary["HitRate@5"] = cat_summary["HitRate@5"].round(2)
    cat_summary["Recall@5"] = cat_summary["Recall@5"].round(2)
    cat_summary["P@5"] = cat_summary["P@5"].round(2)
    cat_summary["Latency_ms"] = cat_summary["Latency_ms"].round(2)

    # Print Terminal Report
    print("\n" + "=" * 90)
    print("📊 RETRIEVAL BENCHMARK SUMMARY (OVERALL RESULTS)")
    print("=" * 90)
    print(df_summary.to_string(index=False))
    print("=" * 90)

    # Export to Excel
    if output_excel:
        output_excel.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="Summary Comparison", index=False)
            cat_summary.to_excel(writer, sheet_name="Category Breakdown", index=False)
            df_all.to_excel(writer, sheet_name="All Query Logs", index=False)
        print(f"\n💾 Excel Report saved successfully: {output_excel}")

    # Generate Publication-Ready Charts
    if output_chart:
        output_chart.parent.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Academic Senior Project QA: Retrieval Performance Benchmark (Chapter 4)",
            fontsize=16,
            fontweight="bold",
        )

        colors = ["#e74c3c", "#f39c12", "#2980b9", "#27ae60"]

        # Subplot 1: MRR & Hit Rate@5 Comparison
        x = np.arange(len(methods))
        width = 0.35
        axes[0, 0].bar(x - width/2, df_summary["MRR"] * 100, width, label="MRR (x100)", color="#3498db")
        axes[0, 0].bar(x + width/2, df_summary["Hit Rate@5 (%)"], width, label="Hit Rate@5 (%)", color="#2ecc71")
        axes[0, 0].set_title("MRR & Hit Rate@5 across Retrieval Methods", fontweight="bold")
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(["Dense", "BM25", "True Hybrid", "Hybrid+Rerank"], rotation=10)
        axes[0, 0].set_ylim(0, 115)
        axes[0, 0].legend()
        axes[0, 0].grid(axis="y", linestyle="--", alpha=0.7)

        # Subplot 2: Recall@K Progression (K=1, 3, 5, 10)
        k_labels = ["Recall@1", "Recall@3", "Recall@5", "Recall@10"]
        for idx, m in enumerate(methods):
            m_data = df_summary[df_summary["Retrieval Method"] == m]
            rec_vals = [m_data[f"{k} (%)"].values[0] for k in k_labels]
            axes[0, 1].plot(k_labels, rec_vals, marker="o", linewidth=2.5, label=m, color=colors[idx])
        axes[0, 1].set_title("Recall@K Progression Curve", fontweight="bold")
        axes[0, 1].set_ylabel("Recall (%)")
        axes[0, 1].set_ylim(0, 105)
        axes[0, 1].legend()
        axes[0, 1].grid(True, linestyle="--", alpha=0.7)

        # Subplot 3: Category MRR Comparison
        cat_pivot = cat_summary.pivot(index="Category", columns="Method", values="MRR")
        cat_pivot.plot(kind="bar", ax=axes[1, 0], colormap="viridis", width=0.8)
        axes[1, 0].set_title("MRR by Query Category", fontweight="bold")
        axes[1, 0].set_ylabel("MRR Score")
        axes[1, 0].set_xticklabels(cat_pivot.index, rotation=15, ha="right")
        axes[1, 0].grid(axis="y", linestyle="--", alpha=0.7)
        axes[1, 0].legend(fontsize=8)

        # Subplot 4: Latency vs Accuracy (MRR) Trade-off
        axes[1, 1].scatter(
            df_summary["Avg Latency (ms)"],
            df_summary["MRR"],
            s=220,
            c=colors,
            edgecolor="black",
            zorder=5,
        )
        for i, m in enumerate(methods):
            axes[1, 1].annotate(
                m,
                (df_summary["Avg Latency (ms)"][i] + 0.5, df_summary["MRR"][i] + 0.01),
                fontweight="bold",
                fontsize=10,
            )
        axes[1, 1].set_title("Latency (ms) vs MRR Trade-off", fontweight="bold")
        axes[1, 1].set_xlabel("Average Query Latency (ms)")
        axes[1, 1].set_ylabel("Mean Reciprocal Rank (MRR)")
        axes[1, 1].grid(True, linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig(output_chart, dpi=300)
        plt.close()
        print(f"📊 Visualization Chart saved successfully: {output_chart}\n")

    return df_summary


def interactive_retrieval_menu():
    """Interactive CLI menu in Terminal for retrieval evaluations."""
    gt_file = PROJECT_ROOT / "backend" / "data" / "retrieval_ground_truth.json"
    output_excel = PROJECT_ROOT / "backend" / "data" / "retrieval_evaluation.xlsx"
    output_chart = PROJECT_ROOT / "backend" / "data" / "retrieval_evaluation_charts.png"

    if not gt_file.exists():
        gt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(gt_file, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_GROUND_TRUTH_QUERIES, f, ensure_ascii=False, indent=2)

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    while True:
        print("\n" + "=" * 70)
        print("🔍 RETRIEVAL BENCHMARK EVALUATION SUITE (Chapter 4 System Evaluation)")
        print("=" * 70)
        print("Menu Options:")
        print("  [1] Run Full Benchmark (Dense vs BM25 vs Hybrid vs Reranker)")
        print("  [2] Quick A/B Compare (Dense Only vs True Hybrid)")
        print("  [3] Inspect a Specific Query by ID")
        print("  [4] Reset/Regenerate Ground Truth Query Dataset")
        print("  [q] Exit")
        print("-" * 70)

        choice = input("👉 Enter choice [1, 2, 3, 4, q]: ").strip().lower()

        if choice == "1":
            run_full_retrieval_benchmark(ground_truth, output_excel, output_chart)

        elif choice == "2":
            quick_methods = ["Dense Only", "True Hybrid (RRF)"]
            print(f"\n⚡ Running Quick A/B Test on {len(ground_truth)} queries...")
            quick_records = []
            for m in quick_methods:
                for q_item in ground_truth:
                    quick_records.append(evaluate_query_retrieval(q_item, method_name=m, top_k=5))
            df_q = pd.DataFrame(quick_records)
            q_sum = df_q.groupby("Method")[["MRR", "HitRate@1", "HitRate@5", "Recall@5", "Latency_ms"]].mean()
            print("\n" + "=" * 65)
            print("⚡ QUICK A/B BENCHMARK RESULT")
            print("=" * 65)
            print(q_sum.round(3).to_string())
            print("=" * 65)

        elif choice == "3":
            print(f"\nAvailable Query IDs (1-{len(ground_truth)}):")
            for q in ground_truth:
                print(f"  [{q['query_id']:02d}] ({q['category']}) : {q['query']}")
            sel = input("\nEnter Query ID: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(ground_truth):
                target_q = ground_truth[int(sel) - 1]
                print(f"\n🔍 Query: {target_q['query']}")
                for m in ["Dense Only", "BM25 Only", "True Hybrid (RRF)", "True Hybrid + Rerank"]:
                    res = evaluate_query_retrieval(target_q, m, top_k=3)
                    print(f"  • {m:<22} | Top-1: {res['Top_1_Source'][:28]:<28} | Hit: {res['Top_1_Success']} | Rank: {res['First_Hit_Rank']} | Latency: {res['Latency_ms']}ms")
                input("\nPress Enter to continue...")

        elif choice == "4":
            with open(gt_file, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_GROUND_TRUTH_QUERIES, f, ensure_ascii=False, indent=2)
            print(f"✅ Ground truth dataset refreshed ({len(DEFAULT_GROUND_TRUTH_QUERIES)} queries).")

        elif choice in ("q", "exit"):
            print("👋 Exiting Evaluation Suite.")
            break


def main():
    parser = argparse.ArgumentParser(description="Academic Retrieval Benchmark Evaluation Suite.")
    parser.add_argument("--all", action="store_true", help="Run full benchmark non-interactively and export results.")
    parser.add_argument("--excel", type=Path, default=PROJECT_ROOT / "backend" / "data" / "retrieval_evaluation.xlsx")
    parser.add_argument("--chart", type=Path, default=PROJECT_ROOT / "backend" / "data" / "retrieval_evaluation_charts.png")
    parser.add_argument("--gt", type=Path, default=PROJECT_ROOT / "backend" / "data" / "retrieval_ground_truth.json")

    args = parser.parse_args()

    if not args.gt.exists():
        args.gt.parent.mkdir(parents=True, exist_ok=True)
        with open(args.gt, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_GROUND_TRUTH_QUERIES, f, ensure_ascii=False, indent=2)

    with open(args.gt, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    if args.all:
        run_full_retrieval_benchmark(ground_truth, args.excel, args.chart)
    else:
        interactive_retrieval_menu()


if __name__ == "__main__":
    main()
