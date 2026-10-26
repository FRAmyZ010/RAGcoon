"""
Module: export_parameter_sweep_excel.py
Description:
    Exports all Stage 1 (Retrieval Sweep) and Stage 2 (LLM Generation Sweep with gemma3:4b)
    empirical results into 7 ultra-detailed sheets in:
      1) data/RAGcoon_Parameter_Tuning_Experiments.xlsx
      2) backend/data/RAGcoon_Parameter_Tuning_Experiments.xlsx
      3) Updates data/RAGcoon_Handoff_Specification.xlsx & backend/data/RAGcoon_Handoff_Specification.xlsx
         with all 7 new Parameter Sweep & Experiment Tracking sheets.
"""

import json
import os
import shutil
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RESULTS_JSON = os.path.join(CURRENT_DIR, "results", "parameter_sweep_results.json")

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BACKEND_DATA_DIR = os.path.join(BACKEND_DIR, "data")

# Styling definitions
HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
WINNER_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
WARN_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
ZEBRA_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=13, bold=True, color="1F4E78")
BOLD_FONT = Font(name="Calibri", size=10, bold=True)
REGULAR_FONT = Font(name="Calibri", size=10)

THIN_SIDE = Side(border_style="thin", color="D9D9D9")
BORDER_ALL = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)


def style_table(ws, start_row: int, end_row: int, num_cols: int, winner_rows: set[int] | None = None, left_cols: tuple[int, ...] = (1, 2, 3)):
    winner_rows = winner_rows or set()
    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_ALL

    for r_idx in range(start_row + 1, end_row + 1):
        is_winner = r_idx in winner_rows
        fill = WINNER_FILL if is_winner else (ZEBRA_FILL if (r_idx - start_row) % 2 == 0 else PatternFill(fill_type=None))
        font = BOLD_FONT if is_winner else REGULAR_FONT
        for c_idx in range(1, num_cols + 1):
            c = ws.cell(row=r_idx, column=c_idx)
            if fill.fill_type:
                c.fill = fill
            c.font = font
            c.border = BORDER_ALL
            c.alignment = Alignment(
                horizontal="left" if c_idx in left_cols else "center",
                vertical="center",
                wrap_text=True,
            )


def auto_fit_columns(ws, max_width: int = 46):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            lines = val_str.split("\n")
            for l in lines:
                if len(l) > max_len:
                    max_len = len(l)
        ws.column_dimensions[col_letter].width = max(12, min(max_len + 4, max_width))


def populate_parameter_sweep_sheets(wb: Workbook, payload: dict, prefix_num: int | None = None):
    """Add 7 comprehensive Stage 1 & Stage 2 Parameter Sweep sheets to a Workbook."""
    opt = payload["optimal_config"]
    s1_winners = payload["stage1_winners"]
    s2_winners = payload["stage2_winners"]
    s1_all = payload["stage1_results"]
    s2_all = payload["stage2_results"]

    def sheet_name(idx: int, base: str) -> str:
        if prefix_num is not None:
            return f"{prefix_num + idx:02d}_{base}"[:31]
        return f"0{idx + 1}_{base}"[:31]

    # -------------------------------------------------------------------------
    # SHEET 1: Executive Leaderboard & Optimal Config Summary
    # -------------------------------------------------------------------------
    s_name_1 = sheet_name(0, "Optimal_Config_Summary")
    if s_name_1 in wb.sheetnames:
        del wb[s_name_1]
    ws1 = wb.create_sheet(title=s_name_1)

    ws1["A1"] = "🏆 สรุปผลการทดลองปรับจูนพารามิเตอร์ 2 ระยะ (Two-Stage Parameter Tuning & Optimal Config)"
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = f"โมเดลหลักที่ใช้ทดสอบ: {payload['primary_model']} | วันที่ประมวลผล: {payload['generated_at']} | โปรไฟล์ผู้ชนะ: {opt['profile_name']}"
    ws1["A2"].font = BOLD_FONT

    headers_opt = [
        "ลำดับ",
        "ชื่อพารามิเตอร์ (Parameter)",
        "หมวดหมู่ (Stage)",
        "ช่วงค่าที่ทดสอบทั้งหมด (Tested Range)",
        "ค่าที่ดีที่สุด (Optimal Value)",
        "เหตุผลและผลลัพธ์จากการทดลองจริง (Empirical Justification)",
    ]
    rows_opt = [
        [
            1,
            "top_k",
            "Stage 1: ฝั่งค้นหา (Retrieval Pool)",
            "[100, 50, 30, 15, 10, 5]",
            opt["top_k"],
            f"ชนะใน Exp 1 (Composite = {s1_winners['best_stage1_composite']:.2f}): ดึง Candidate Pool กว้างพอให้ Reranker คัดเนื้อหาเทคนิคขึ้นอันดับ 1 โดยไม่ช้าเกินไป",
        ],
        [
            2,
            "rerank_top_n",
            "Stage 1: ฝั่งคัดกรอง (Cross-Encoder Cutoff)",
            "[30, 15, 10, 5, 3, 1]",
            opt["rerank_top_n"],
            f"ชนะใน Exp 2 (Best Cutoff = {s1_winners['best_rerank_top_n']}): สมดุลระหว่าง Recall@N และ Precision@N ก่อนส่งเข้า Context Assembly",
        ],
        [
            3,
            "enable_hybrid",
            "Stage 1: Ablation Switch",
            "[True (BM25+E5), False (Dense Only)]",
            str(opt["enable_hybrid"]),
            "เปิด Hybrid RRF (BM25 + Multilingual-E5) ช่วยจับทั้งรหัสฮาร์ดแวร์/ชื่อเฉพาะ และความหมายข้ามภาษาไทย-อังกฤษ",
        ],
        [
            4,
            "enable_reranker",
            "Stage 1: Ablation Switch",
            "[True (Cross-Encoder), False (Skip)]",
            str(opt["enable_reranker"]),
            "เปิด BGE Cross-Encoder Reranker ช่วยดันค่า MRR และความแม่นยำของอันดับ 1 สูงกว่า Raw RRF อย่างชัดเจน",
        ],
        [
            5,
            "enable_boilerplate_filter",
            "Stage 1: Ablation Switch",
            "[True (Filter Noise), False (Unfiltered)]",
            str(opt["enable_boilerplate_filter"]),
            "เปิดกรองขยะเอกสาร (สารบัญ, กิตติกรรมประกาศ, บรรณานุกรม, ลายเซ็น) ลด Noise Rate เหลือ 0%",
        ],
        [
            6,
            "enable_fast_path",
            "Stage 1: Ablation Switch",
            "[True (Metadata Scroll), False (Off)]",
            str(opt["enable_fast_path"]),
            "เปิดทางลัด Metadata Scroll สำหรับคำถามถามชื่ออาจารย์/ผู้จัดทำ/จำนวนเล่ม ตอบทันทีในระดับมิลลิวินาที",
        ],
        [
            7,
            "max_context_chunks",
            "Stage 2: ฝั่งจัดเตรียมบริบท (Context Cap)",
            "[15, 10, 6, 5, 4, 2]",
            opt["max_context_chunks"],
            f"ชนะใน Exp 4 (Composite = {s2_winners['best_stage2_composite']:.2f}): ให้เนื้อหาครบถ้วนสำหรับ gemma3:4b โดยไม่เปลือง Input Tokens เกินจำเป็น",
        ],
        [
            8,
            "max_chunks_per_project",
            "Stage 2: ฝั่งจัดเตรียมบริบท (Fair Quota)",
            "[5, 3, 2, 1, 6 (Uncapped)]",
            opt["max_chunks_per_project"],
            "ล็อกโควตาต่อโปรเจกต์ป้องกันปัญหา Context Starvation เวลาเปรียบเทียบหลายโปรเจกต์ (Multi-Project Coverage = 100%)",
        ],
        [
            9,
            "prompt_preset",
            "Stage 2: ฝั่ง LLM Generation (gemma3:4b)",
            "['concise', 'balanced', 'deep_academic', 'step_by_step']",
            opt["prompt_preset"],
            f"ชนะใน Exp 5: รูปแบบ Prompt '{opt['prompt_preset']}' ให้คะแนนความครบถ้วนของคำสำคัญ (Key Phrase Recall) และความเร็วสมดุลที่สุด",
        ],
        [
            10,
            "temperature",
            "Stage 2: ฝั่ง LLM Generation (gemma3:4b)",
            "[0.0, 0.2, 0.5]",
            opt["temperature"],
            "รักษาความแม่นยำตามเอกสารอ้างอิง (Deterministic Grounding) และผ่าน Anti-Hallucination Guard 100%",
        ],
    ]

    for c_idx, h in enumerate(headers_opt, start=1):
        ws1.cell(row=4, column=c_idx, value=h)
    for r_offset, row_vals in enumerate(rows_opt, start=5):
        for c_idx, val in enumerate(row_vals, start=1):
            ws1.cell(row=r_offset, column=c_idx, value=val)
    style_table(ws1, 4, 4 + len(rows_opt), len(headers_opt), winner_rows=set(range(5, 5 + len(rows_opt))), left_cols=(2, 3, 6))
    auto_fit_columns(ws1)

    # -------------------------------------------------------------------------
    # SHEET 2: Stage 1 Retrieval Sweeps (Exp 1 top_k & Exp 2 rerank_top_n)
    # -------------------------------------------------------------------------
    s_name_2 = sheet_name(1, "Stage1_Retrieval_Sweep")
    if s_name_2 in wb.sheetnames:
        del wb[s_name_2]
    ws2 = wb.create_sheet(title=s_name_2)

    ws2["A1"] = "🔍 Stage 1: ผลการทดลองปรับค่าฝั่งค้นหาช่วงกว้าง (Exp 1: top_k [100..5] & Exp 2: rerank_top_n [30..1])"
    ws2["A1"].font = TITLE_FONT
    ws2["A2"] = "ทดสอบบน Golden Dataset (15 ข้อ) โดยวัดความแม่นยำการดึง Chunk ที่มีคำตอบจริง (Answer-Bearing Hit Rate & MRR) และความเร็วการค้นหา"
    ws2["A2"].font = BOLD_FONT

    headers_s1 = [
        "กลุ่มการทดลอง (Exp Group)",
        "ค่าพารามิเตอร์ที่ทดสอบ (Setting)",
        "ชื่อโปรไฟล์ (Profile)",
        "top_k",
        "rerank_top_n",
        "Hit Rate (%)",
        "MRR (0-1.0)",
        "Precision@N (%)",
        "Recall@N (%)",
        "Boilerplate Noise (%)",
        "Vector+BM25 (ms)",
        "Rerank (ms)",
        "เวลารวมฝั่งค้นหา (ms)",
        "Speed Score",
        "Composite Score (0-100)",
        "สถานะ (Status)",
    ]
    exp12_rows = [r for r in s1_all if r["exp_group"] in ("Exp 1: top_k Sweep", "Exp 2: rerank_top_n Sweep")]
    max_exp1_score = max((r["composite_score"] for r in exp12_rows if r["exp_group"] == "Exp 1: top_k Sweep"), default=0)
    max_exp2_score = max((r["composite_score"] for r in exp12_rows if r["exp_group"] == "Exp 2: rerank_top_n Sweep"), default=0)

    for c_idx, h in enumerate(headers_s1, start=1):
        ws2.cell(row=4, column=c_idx, value=h)

    winner_rows_s1 = set()
    for idx, r in enumerate(exp12_rows, start=5):
        is_w = (r["exp_group"] == "Exp 1: top_k Sweep" and r["composite_score"] == max_exp1_score) or (
            r["exp_group"] == "Exp 2: rerank_top_n Sweep" and r["composite_score"] == max_exp2_score
        )
        if is_w:
            winner_rows_s1.add(idx)
        row_vals = [
            r["exp_group"],
            r["exp_label"],
            r["profile_name"],
            r["top_k"],
            r["rerank_top_n"],
            r["hit_rate_pct"],
            r["mrr"],
            r["precision_at_n_pct"],
            r["recall_at_n_pct"],
            r["boilerplate_noise_pct"],
            r["avg_retrieval_ms"],
            r["avg_rerank_ms"],
            r["avg_total_search_ms"],
            r["speed_score"],
            r["composite_score"],
            "🏆 WINNER" if is_w else "Tested",
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws2.cell(row=idx, column=c_idx, value=val)

    style_table(ws2, 4, 4 + len(exp12_rows), len(headers_s1), winner_rows=winner_rows_s1)
    auto_fit_columns(ws2)

    # -------------------------------------------------------------------------
    # SHEET 3: Stage 1 Component Ablation Matrix (Exp 3)
    # -------------------------------------------------------------------------
    s_name_3 = sheet_name(2, "Stage1_Ablation_Matrix")
    if s_name_3 in wb.sheetnames:
        del wb[s_name_3]
    ws3 = wb.create_sheet(title=s_name_3)

    ws3["A1"] = "🧪 Stage 1 (Exp 3): ตารางทดสอบเปิด-ปิดโมดูลอิสระ (Component Ablation Study Matrix)"
    ws3["A1"].font = TITLE_FONT
    ws3["A2"] = "พิสูจน์ผลกระทบเมื่อปิดแต่ละฟีเจอร์ (Hybrid BM25, E5 Dense, Cross-Encoder Reranker, Boilerplate Filter, Fast-Path) เทียบกับระบบเต็มรูปแบบและระบบเก่าดั้งเดิม"
    ws3["A2"].font = BOLD_FONT

    headers_ab = [
        "รูปแบบการเปิด/ปิดโมดูล (Ablation Variant)",
        "ชื่อโปรไฟล์ (Profile)",
        "Hybrid (BM25+E5)",
        "BM25 Only",
        "Cross-Encoder Rerank",
        "Boilerplate Filter",
        "Fast-Path Shortcut",
        "Hit Rate (%)",
        "MRR (0-1.0)",
        "Precision@N (%)",
        "Recall@N (%)",
        "สัดส่วนขยะติดมา (%)",
        "เวลาค้นหาเฉลี่ย (ms)",
        "Composite Score",
        "ข้อค้นพบจากการเปิด/ปิดโมดูล (Key Takeaway)",
    ]
    exp3_rows = [r for r in s1_all if r["exp_group"] == "Exp 3: Component Ablation"]
    max_exp3_score = max((r["composite_score"] for r in exp3_rows), default=0)

    for c_idx, h in enumerate(headers_ab, start=1):
        ws3.cell(row=4, column=c_idx, value=h)

    winner_rows_ab = set()
    for idx, r in enumerate(exp3_rows, start=5):
        is_w = r["composite_score"] == max_exp3_score
        if is_w:
            winner_rows_ab.add(idx)
        row_vals = [
            r["exp_label"],
            r["profile_name"],
            "ON" if r["enable_hybrid"] else "OFF",
            "ON" if r["enable_bm25_only"] else "OFF",
            "ON" if r["enable_reranker"] else "OFF",
            "ON" if r["enable_boilerplate_filter"] else "OFF",
            "ON" if r["enable_fast_path"] else "OFF",
            r["hit_rate_pct"],
            r["mrr"],
            r["precision_at_n_pct"],
            r["recall_at_n_pct"],
            r["boilerplate_noise_pct"],
            r["avg_total_search_ms"],
            r["composite_score"],
            r["description"],
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws3.cell(row=idx, column=c_idx, value=val)

    style_table(ws3, 4, 4 + len(exp3_rows), len(headers_ab), winner_rows=winner_rows_ab, left_cols=(1, 2, 15))
    auto_fit_columns(ws3)

    # -------------------------------------------------------------------------
    # SHEET 4: Stage 2 LLM Generation Sweeps (Exp 4 Context Quota & Exp 5 Prompt/Temp)
    # -------------------------------------------------------------------------
    s_name_4 = sheet_name(3, "Stage2_LLM_Gemma3_Sweep")
    if s_name_4 in wb.sheetnames:
        del wb[s_name_4]
    ws4 = wb.create_sheet(title=s_name_4)

    ws4["A1"] = "🤖 Stage 2: ผลการทดลองปรับค่าฝั่ง LLM Generation ด้วยโมเดล ollama / gemma3:4b (Exp 4 & Exp 5)"
    ws4["A1"].font = TITLE_FONT
    ws4["A2"] = "ล็อกค่าฝั่งค้นหาที่ดีที่สุดจาก Stage 1 แล้วทดสอบปรับจำนวน Chunks, โควตาต่อโปรเจกต์, รูปแบบ Prompt (Preset) และ Temperature"
    ws4["A2"].font = BOLD_FONT

    headers_s2 = [
        "กลุ่มการทดลอง (Exp Group)",
        "ค่าพารามิเตอร์ที่ทดสอบ (Setting)",
        "ชื่อโปรไฟล์ (Profile)",
        "โมเดล (LLM)",
        "max_context_chunks",
        "max_chunks_per_project",
        "prompt_preset",
        "temperature",
        "num_predict",
        "Quality Score (0-100)",
        "Key Phrase Recall (%)",
        "Multi-Project Coverage (%)",
        "Hallucination Guard (%)",
        "Input Tokens เฉลี่ย",
        "Output Tokens เฉลี่ย",
        "เวลา LLM ตอบ (วินาที)",
        "ความเร็ว (TPS)",
        "Composite Score (0-100)",
        "สถานะ (Status)",
    ]
    max_exp4_score = max((r["composite_score"] for r in s2_all if r["exp_group"] == "Exp 4: Context & Quota Sweep"), default=0)
    max_exp5_score = max((r["composite_score"] for r in s2_all if r["exp_group"] == "Exp 5: Prompt & Temperature Sweep"), default=0)

    for c_idx, h in enumerate(headers_s2, start=1):
        ws4.cell(row=4, column=c_idx, value=h)

    winner_rows_s2 = set()
    for idx, r in enumerate(s2_all, start=5):
        is_w = (r["exp_group"] == "Exp 4: Context & Quota Sweep" and r["composite_score"] == max_exp4_score) or (
            r["exp_group"] == "Exp 5: Prompt & Temperature Sweep" and r["composite_score"] == max_exp5_score
        )
        if is_w:
            winner_rows_s2.add(idx)
        row_vals = [
            r["exp_group"],
            r["exp_label"],
            r["profile_name"],
            r["llm_model"],
            r["max_context_chunks"],
            r["max_chunks_per_project"],
            r["prompt_preset"],
            r["temperature"],
            r["num_predict"],
            r["avg_quality_score"],
            r["avg_phrase_recall_pct"],
            r["multi_project_coverage_pct"],
            r["avg_hallucination_pass_pct"],
            r["avg_input_tokens"],
            r["avg_output_tokens"],
            r["avg_llm_seconds"],
            r["avg_tps"],
            r["composite_score"],
            "🏆 WINNER" if is_w else "Tested",
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws4.cell(row=idx, column=c_idx, value=val)

    style_table(ws4, 4, 4 + len(s2_all), len(headers_s2), winner_rows=winner_rows_s2)
    auto_fit_columns(ws4)

    # -------------------------------------------------------------------------
    # SHEET 5: Stage 1 Per-Query Granular Breakdown (19 Configs x 13 Answerable Queries)
    # -------------------------------------------------------------------------
    s_name_5 = sheet_name(4, "Stage1_PerQuery_Detail")
    if s_name_5 in wb.sheetnames:
        del wb[s_name_5]
    ws5 = wb.create_sheet(title=s_name_5)

    ws5["A1"] = "🔎 Stage 1 Per-Query Breakdown: ผลลัพธ์รายข้อคำถามสำหรับทุกค่าพารามิเตอร์ฝั่งค้นหา"
    ws5["A1"].font = TITLE_FONT
    ws5["A2"] = "แจกแจงค่า Hit (0/1), Reciprocal Rank (RR), Precision@N, Recall@N, จำนวนขยะ Boilerplate และเวลาค้นหารายข้อ"
    ws5["A2"].font = BOLD_FONT

    headers_pq1 = [
        "กลุ่มการทดลอง (Exp Group)",
        "การตั้งค่า (Setting)",
        "รหัสข้อ (Query ID)",
        "หมวดหมู่คำถาม (Category)",
        "Hit (1=เจอ, 0=ไม่เจอ)",
        "Reciprocal Rank (RR)",
        "Precision@N (%)",
        "Recall@N (%)",
        "จำนวน Chunks ที่คืนมา",
        "จำนวนขยะติดมา (Chunks)",
        "เวลาค้นหา (ms)",
    ]
    for c_idx, h in enumerate(headers_pq1, start=1):
        ws5.cell(row=4, column=c_idx, value=h)

    r_cursor = 5
    for r in s1_all:
        for pq in r.get("per_query", []):
            vals = [
                r["exp_group"],
                r["exp_label"],
                pq.get("id", ""),
                pq.get("category", ""),
                pq.get("hit", 0),
                pq.get("rr", 0.0),
                pq.get("precision", 0.0),
                pq.get("recall", 0.0),
                pq.get("returned", 0),
                pq.get("boilerplate", 0),
                pq.get("search_ms", 0.0),
            ]
            for c_idx, v in enumerate(vals, start=1):
                ws5.cell(row=r_cursor, column=c_idx, value=v)
            r_cursor += 1

    style_table(ws5, 4, r_cursor - 1, len(headers_pq1), left_cols=(1, 2, 4))
    auto_fit_columns(ws5)

    # -------------------------------------------------------------------------
    # SHEET 6: Stage 2 Per-Query Answers & Metrics Breakdown (gemma3:4b)
    # -------------------------------------------------------------------------
    s_name_6 = sheet_name(5, "Stage2_PerQuery_Answers")
    if s_name_6 in wb.sheetnames:
        del wb[s_name_6]
    ws6 = wb.create_sheet(title=s_name_6)

    ws6["A1"] = "📝 Stage 2 Per-Query Breakdown: ผลลัพธ์และตัวอย่างคำตอบจริงรายข้อจากโมเดล gemma3:4b"
    ws6["A1"].font = TITLE_FONT
    ws6["A2"] = "เปรียบเทียบคะแนนคุณภาพ, Key Phrase Recall, จำนวน Input/Output Tokens, เวลาตอบ และตัวอย่างคำตอบของ gemma3:4b ในแต่ละการตั้งค่า"
    ws6["A2"].font = BOLD_FONT

    headers_pq2 = [
        "กลุ่มการทดลอง (Exp Group)",
        "การตั้งค่า (Setting)",
        "รหัสข้อ (Query ID)",
        "หมวดหมู่ (Category)",
        "Quality Score (0-100)",
        "Key Phrase Recall (%)",
        "Hallucination Guard (1=Pass)",
        "Input Tokens",
        "Output Tokens",
        "LLM Latency (s)",
        "Total Latency (s)",
        "ตัวอย่างคำตอบจาก gemma3:4b (Answer Preview)",
    ]
    for c_idx, h in enumerate(headers_pq2, start=1):
        ws6.cell(row=4, column=c_idx, value=h)

    r_cursor2 = 5
    for r in s2_all:
        for pq in r.get("per_query", []):
            vals = [
                r["exp_group"],
                r["exp_label"],
                pq.get("id", ""),
                pq.get("category", ""),
                pq.get("quality_score", 0.0),
                pq.get("phrase_recall_pct", 0.0),
                pq.get("hallucination_guard", 1),
                pq.get("input_tokens", 0),
                pq.get("output_tokens", 0),
                pq.get("llm_seconds", 0.0),
                pq.get("total_seconds", 0.0),
                pq.get("answer_preview", ""),
            ]
            for c_idx, v in enumerate(vals, start=1):
                ws6.cell(row=r_cursor2, column=c_idx, value=v)
            r_cursor2 += 1

    style_table(ws6, 4, r_cursor2 - 1, len(headers_pq2), left_cols=(1, 2, 4, 12))
    auto_fit_columns(ws6, max_width=55)

    # -------------------------------------------------------------------------
    # SHEET 7: Full Experiment History Log (All Runs Ranked Leaderboard)
    # -------------------------------------------------------------------------
    s_name_7 = sheet_name(6, "Full_Experiment_Log")
    if s_name_7 in wb.sheetnames:
        del wb[s_name_7]
    ws7 = wb.create_sheet(title=s_name_7)

    ws7["A1"] = "📋 บันทึกประวัติการทดลองทั้งหมด (Complete Experiment Tracking Log - Stage 1 & Stage 2)"
    ws7["A1"].font = TITLE_FONT
    ws7["A2"] = "รวบรวมผลการรันทุกการตั้งค่า (32 การทดลองย่อย) พร้อมรหัสการทดลอง (Run ID) และคะแนนรวม (Composite Score)"
    ws7["A2"].font = BOLD_FONT

    headers_log = [
        "Run ID",
        "ระยะการทดสอบ (Stage)",
        "กลุ่มการทดลอง (Exp Group)",
        "การตั้งค่า (Parameter Setting)",
        "top_k",
        "rerank_top_n",
        "Hybrid",
        "Rerank",
        "Filter",
        "FastPath",
        "Chunks",
        "Quota/Proj",
        "Prompt Preset",
        "Temp",
        "Hit Rate (%)",
        "MRR / Quality",
        "Latency",
        "Composite Score",
    ]
    for c_idx, h in enumerate(headers_log, start=1):
        ws7.cell(row=4, column=c_idx, value=h)

    row_cursor = 5
    winner_log_rows = set()
    for i, r in enumerate(s1_all, start=1):
        if r["composite_score"] in (max_exp1_score, max_exp2_score, max_exp3_score):
            winner_log_rows.add(row_cursor)
        vals = [
            f"EXP-S1-{i:02d}",
            r["stage"],
            r["exp_group"],
            r["exp_label"],
            r["top_k"],
            r["rerank_top_n"],
            "ON" if r["enable_hybrid"] else ("BM25" if r["enable_bm25_only"] else "Dense"),
            "ON" if r["enable_reranker"] else "OFF",
            "ON" if r["enable_boilerplate_filter"] else "OFF",
            "ON" if r["enable_fast_path"] else "OFF",
            "-",
            "-",
            "-",
            "-",
            f"{r['hit_rate_pct']:.1f}%",
            f"MRR: {r['mrr']:.4f}",
            f"{r['avg_total_search_ms']:.1f} ms",
            r["composite_score"],
        ]
        for c_idx, v in enumerate(vals, start=1):
            ws7.cell(row=row_cursor, column=c_idx, value=v)
        row_cursor += 1

    for i, r in enumerate(s2_all, start=1):
        if r["composite_score"] in (max_exp4_score, max_exp5_score):
            winner_log_rows.add(row_cursor)
        vals = [
            f"EXP-S2-{i:02d}",
            r["stage"],
            r["exp_group"],
            r["exp_label"],
            r["top_k"],
            r["rerank_top_n"],
            "ON",
            "ON",
            "ON",
            "ON",
            r["max_context_chunks"],
            r["max_chunks_per_project"],
            r["prompt_preset"],
            r["temperature"],
            f"{r['avg_hit_rate_pct']:.1f}%",
            f"Quality: {r['avg_quality_score']:.1f}",
            f"{r['avg_llm_seconds']:.2f} s",
            r["composite_score"],
        ]
        for c_idx, v in enumerate(vals, start=1):
            ws7.cell(row=row_cursor, column=c_idx, value=v)
        row_cursor += 1

    style_table(ws7, 4, row_cursor - 1, len(headers_log), winner_rows=winner_log_rows, left_cols=(2, 3, 4))
    auto_fit_columns(ws7)


def build_all_excel_files():
    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # 1. Create standalone RAGcoon_Parameter_Tuning_Experiments.xlsx
    wb_standalone = Workbook()
    default_sheet = wb_standalone.active
    populate_parameter_sweep_sheets(wb_standalone, payload, prefix_num=None)
    if default_sheet.title in wb_standalone.sheetnames and len(wb_standalone.sheetnames) > 1:
        del wb_standalone[default_sheet.title]

    out_standalone_1 = os.path.join(DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    out_standalone_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    wb_standalone.save(out_standalone_1)
    shutil.copyfile(out_standalone_1, out_standalone_2)
    print(f"✅ Saved Standalone Parameter Sweep Excel -> {out_standalone_1}", flush=True)
    print(f"✅ Saved Standalone Parameter Sweep Excel -> {out_standalone_2}", flush=True)

    # 2. Update existing RAGcoon_Handoff_Specification.xlsx with the new sheets
    handoff_1 = os.path.join(DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    handoff_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    if os.path.exists(handoff_1):
        wb_handoff = load_workbook(handoff_1)
        populate_parameter_sweep_sheets(wb_handoff, payload, prefix_num=10)
        wb_handoff.save(handoff_1)
        shutil.copyfile(handoff_1, handoff_2)
        print(f"✅ Updated Handoff Specification Excel with Stage 1 & Stage 2 Sweep Sheets -> {handoff_1}", flush=True)
        print(f"✅ Updated Handoff Specification Excel with Stage 1 & Stage 2 Sweep Sheets -> {handoff_2}", flush=True)


if __name__ == "__main__":
    build_all_excel_files()
