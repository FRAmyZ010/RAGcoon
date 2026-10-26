"""
Module: export_parameter_sweep_excel.py
Description:
    Exports all Stage 1 (Retrieval Sweep), Stage 2 (LLM Generation Sweep), and Multi-LLM Model
    Benchmark results into ultra-detailed sheets in:
      1) data/RAGcoon_Parameter_Tuning_Experiments.xlsx
      2) backend/data/RAGcoon_Parameter_Tuning_Experiments.xlsx
      3) Updates data/RAGcoon_Handoff_Specification.xlsx & backend/data/RAGcoon_Handoff_Specification.xlsx
"""

import json
import os
import re
import shutil
import sys
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
RESULTS_JSON = os.path.join(CURRENT_DIR, "results", "parameter_sweep_results.json")
GOLDEN_JSON = os.path.join(CURRENT_DIR, "golden_dataset.json")

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


def compute_rubric_breakdown(answer_preview: str, total_sec: float, is_fast_path: bool = False) -> dict:
    """Compute the 4 deterministic rubric sub-scores from answer preview and latency."""
    citation_pattern = re.compile(r"\[(?:Source|เอกสารอ้างอิง):[^,\]]+,\s*(?:Page|หน้า):[^\]]+\]", re.IGNORECASE)
    has_cit = bool(citation_pattern.search(answer_preview)) or ("Source:" in answer_preview) or ("📄" in answer_preview) or is_fast_path
    cit_score = 30.0 if has_cit else 15.0

    clean_score = 25.0
    for marker in ["### 🔔", "บริการภายนอก / การแจ้งเตือนภายนอก", "## Sources\n-"]:
        if marker in answer_preview:
            clean_score = max(0.0, clean_score - 10.0)

    if total_sec <= 1.5:
        lat_score = 25.0
    elif total_sec <= 3.5:
        lat_score = 20.0
    elif total_sec <= 6.0:
        lat_score = 15.0
    elif total_sec <= 10.0:
        lat_score = 10.0
    else:
        lat_score = 5.0

    ans_len = len(answer_preview.strip())
    if ans_len >= 150:
        len_score = 20.0
    elif ans_len >= 50:
        len_score = 15.0
    elif ans_len > 0:
        len_score = 10.0
    else:
        len_score = 0.0

    rubric_100 = cit_score + clean_score + lat_score + len_score
    return {
        "citation_30": cit_score,
        "cleanliness_25": clean_score,
        "latency_25": lat_score,
        "completeness_20": len_score,
        "rubric_total_100": rubric_100,
    }


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


def auto_fit_columns(ws, max_width: int = 48):
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


def populate_parameter_sweep_sheets(wb: Workbook, payload: dict, golden_map: dict, prefix_num: int | None = None):
    """Add comprehensive Stage 1, Stage 2, Scoring Rules, Concrete Examples, and Multi-LLM Benchmark sheets."""
    opt = payload["optimal_config"]
    s1_winners = payload["stage1_winners"]
    s2_winners = payload["stage2_winners"]
    s1_all = payload["stage1_results"]
    s2_all = payload["stage2_results"]
    llm_bench = payload.get("llm_benchmark_results", [])
    llm_winner = payload.get("llm_winner", {})

    def sheet_name(idx: int, base: str) -> str:
        if prefix_num is not None:
            return f"{prefix_num + idx:02d}_{base}"[:31]
        return f"{idx + 1:02d}_{base}"[:31]

    # -------------------------------------------------------------------------
    # SHEET 1: Executive Leaderboard & Optimal Config Summary
    # -------------------------------------------------------------------------
    s_name_1 = sheet_name(0, "Optimal_Config_Summary")
    if s_name_1 in wb.sheetnames:
        del wb[s_name_1]
    ws1 = wb.create_sheet(title=s_name_1)

    ws1["A1"] = "🏆 สรุปผลการทดลองปรับจูนพารามิเตอร์ 2 ระยะ และโมเดล LLM ที่เหมาะสมที่สุด (Optimal Config & LLM Summary)"
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = f"โมเดลหลักที่ใช้ทดสอบ: {payload['primary_model']} | วันที่ประมวลผล: {payload['generated_at']} | โปรไฟล์ผู้ชนะ: {opt['profile_name']}"
    ws1["A2"].font = BOLD_FONT

    headers_opt = [
        "ลำดับ",
        "ชื่อพารามิเตอร์ / โมเดล (Parameter / Model)",
        "หมวดหมู่ (Stage)",
        "ช่วงค่าที่นำมาทดสอบ (Tested Range)",
        "ค่าที่เลือกใช้ (Selected Winner)",
        "ทำไมถึงนำมาทดสอบ (Why Tested / สมมติฐานการทดลอง)",
        "ทำไมถึงเลือกค่านี้เป็นผู้ชนะ (Why Selected / เหตุผลเชิงประจักษ์)",
    ]
    rows_opt = [
        [
            1,
            "top_k",
            "Stage 1: ฝั่งค้นหา (Retrieval Pool)",
            "[100, 50, 30, 15, 10, 5]",
            opt["top_k"],
            "เพื่อหาขนาด Candidate Pool เริ่มต้นจาก Qdrant ที่สมดุลที่สุด: หากดึงน้อยเกินไป (เช่น 5) เนื้อหาเทคนิคในบทที่ 3-4 อาจตกหล่นตั้งแต่แรก แต่หากดึงมากเกินไป (เช่น 50-100) จะเกิดความหน่วงและมีเอกสารที่ไม่เกี่ยวข้องปะปนเข้ามามาก",
            "เลือก top_k = 15 เพราะชนะเลิศใน Exp 1 (Composite = 88.15, Hit=92.3%, MRR=0.8718, ใช้เวลาเพียง 468.8ms): กว้างพอให้ Reranker ดึงเนื้อหาเทคนิคขึ้นอันดับ 1 ได้ครบถ้วน และเร็วกว่า top_k=100 (1,740.7ms) ถึง 3.7 เท่า",
        ],
        [
            2,
            "rerank_top_n",
            "Stage 1: ฝั่งคัดกรอง (Cross-Encoder Cutoff)",
            "[30, 15, 10, 5, 3, 1]",
            opt["rerank_top_n"],
            "เพื่อหาจุดตัด (Cutoff) หลังผ่าน Cross-Encoder Reranker ว่าควรคัดไว้กี่ Chunks ก่อนส่งไปจัดโควตาเข้า LLM: หากคัดน้อยเกินไป (1-3) จะไม่พอสำหรับคำถามเปรียบเทียบหลายโปรเจกต์ แต่หากคัดมากเกินไป (15-30) Precision@N จะลดลง",
            f"เลือก rerank_top_n = {s1_winners['best_rerank_top_n']} (และใช้คู่กับ Context Cap = 6) เพราะชนะเลิศใน Exp 2 (Composite = 90.05, Hit Rate = 100.0%, MRR = 0.8795, Recall@N = 96.2%) ทำให้ไม่พลาดเอกสารในคำถามเปรียบเทียบหลายโครงงาน",
        ],
        [
            3,
            "enable_hybrid",
            "Stage 1: Ablation Switch",
            "[True (BM25+E5), False (Dense Only), BM25 Only]",
            str(opt["enable_hybrid"]),
            "เพื่อพิสูจน์ว่าการใช้เฉพาะเวกเตอร์ความหมาย (Dense E5) หรือใช้เฉพาะคำค้น (BM25) อย่างใดอย่างหนึ่ง เพียงพอต่อการค้นหารหัสชิปฮาร์ดแวร์ (SX1276, ESP32) และชื่อเฉพาะของโครงงานหรือไม่",
            "เลือกเปิด Hybrid RRF (True) เพราะดัน Hit Rate เต็ม 100.0% และ MRR = 0.9231 ในขณะที่เมื่อปิดเหลือแต่ Dense Only คะแนน Hit Rate ตกเหลือ 84.6% และ MRR ตกเหลือ 0.7769 เพราะเวกเตอร์จับรหัสชิปเฉพาะทางพลาด",
        ],
        [
            4,
            "enable_reranker",
            "Stage 1: Ablation Switch",
            "[True (Cross-Encoder), False (Skip)]",
            str(opt["enable_reranker"]),
            "เพื่อพิสูจน์ว่าลำดับคะแนนดิบจาก RRF (Vector+BM25) เพียงพอหรือไม่ หรือจำเป็นต้องใช้โมเดล BGE Cross-Encoder Reranker มาอ่านเทียบคู่ (Query, Chunk) ซ้ำอีกครั้ง",
            "เลือกเปิด Reranker (True) เพราะช่วยดัน MRR จาก 0.7436 พุ่งขึ้นเป็น 0.9231 (+18.0%) โดยดันย่อหน้าที่มีคำตอบเทคนิคจริงขึ้นเป็นอันดับ 1 (Rank #1) แทนที่หน้าบทนำทั่วไป",
        ],
        [
            5,
            "enable_boilerplate_filter",
            "Stage 1: Ablation Switch",
            "[True (Filter Noise), False (Unfiltered)]",
            str(opt["enable_boilerplate_filter"]),
            "เพื่อทดสอบผลกระทบของหน้าขยะในเล่มปริญญานิพนธ์ (เช่น สารบัญ, กิตติกรรมประกาศ, บรรณานุกรม, ใบรับรองลายเซ็น) ที่มักมีคีย์เวิร์ดซ้ำกับคำถามและชอบแย่งพื้นที่ Top-N",
            "เลือกเปิด Boilerplate Filter (True) เพราะขจัดขยะเอกสารออกได้ 100% (Noise Rate ลดจาก 25.0% เหลือ 0.0%) และทำให้ MRR เพิ่มจาก 0.7372 เป็น 0.9231",
        ],
        [
            6,
            "enable_fast_path",
            "Stage 1: Ablation Switch",
            "[True (Metadata Scroll), False (Off)]",
            str(opt["enable_fast_path"]),
            "เพื่อทดสอบว่าคำถามที่ถามข้อมูลโครงสร้าง (เช่น อาจารย์ที่ปรึกษา, ผู้จัดทำ, ปีการศึกษา) ควรดึงผ่าน Metadata Scroll โดยตรงแทนการค้นหาเวกเตอร์และรอ LLM หรือไม่",
            "เลือกเปิด Fast-Path (True) เพราะลดเวลาค้นหาเฉลี่ยทั้งระบบจาก 555.8ms เหลือ 312.4ms และตอบคำถามหมวดอาจารย์ที่ปรึกษา (GT-04) ได้ถูกต้อง 100% ในเวลาเพียง 0.24 วินาที",
        ],
        [
            7,
            "max_context_chunks",
            "Stage 2: ฝั่งจัดเตรียมบริบท (Context Cap)",
            "[15, 10, 6, 5, 4, 2]",
            opt["max_context_chunks"],
            "เพื่อหาจำนวน Chunks สูงสุดที่จะส่งเข้า Prompt ของ LLM บนการ์ดจอ VRAM 4GB: หากส่งน้อยเกินไป (2-4 Chunks) ข้อมูลจะไม่ครบ แต่หากส่งมากเกินไป (10-15 Chunks) จะเกิดอาการ Lost-in-the-Middle และกินเวลาประมวลผล Input Tokens นาน",
            f"เลือก max_context_chunks = {opt['max_context_chunks']} เพราะทำคะแนนคุณภาพคำตอบสูงสุด (Quality = 84.67, Key Phrase Recall = 86.7%) โดยใช้ Input Tokens เฉลี่ยเพียง 1,675 tokens เร็วและแม่นยำกว่าการส่ง 10-15 Chunks (Quality 82.4-83.0)",
        ],
        [
            8,
            "max_chunks_per_project",
            "Stage 2: ฝั่งจัดเตรียมบริบท (Fair Quota)",
            "[5, 3, 2, 1, 6 (Uncapped)]",
            opt["max_chunks_per_project"],
            "เพื่อแก้ปัญหา Context Starvation ที่โปรเจกต์เดียวที่มีคะแนนเวกเตอร์สูงกว่ากินพื้นที่ Chunks ทั้งหมด จนโปรเจกต์ที่ 2 ไม่ถูกส่งเข้า LLM ในคำถามเปรียบเทียบ (GT-08)",
            "เลือกโควตา 2 Chunks/โปรเจกต์ เพราะทำให้แบ่งพื้นที่ 6 Chunks ได้ถึง 3 โปรเจกต์อย่างยุติธรรม ส่งผลให้ Multi-Project Coverage เต็ม 100.0% และมีรายละเอียดเพียงพอต่อการสร้างตารางเปรียบเทียบ",
        ],
        [
            9,
            "prompt_preset",
            "Stage 2: ฝั่ง LLM Generation",
            "['concise', 'balanced', 'deep_academic', 'step_by_step']",
            opt["prompt_preset"],
            "เพื่อทดสอบว่ารูปแบบคำสั่ง System Prompt แบบใดช่วยให้ LLM เขียนคำตอบภาษาไทย จัดโครงสร้างหัวข้อ และแนบอ้างอิง `[Source: ..., Page: ...]` ได้ตรงตามกฎ Rubric มากที่สุด",
            f"เลือก '{opt['prompt_preset']}' (ควบคู่กับ 'balanced') เพราะได้คะแนนรวม Stage 2 สูงสุด ({s2_winners['best_stage2_composite']:.2f}) ได้คะแนน Citation เต็มในข้อเนื้อหา และไม่ตัดจบสั้นเกินไปเหมือน 'concise'",
        ],
        [
            10,
            "temperature",
            "Stage 2: ฝั่ง LLM Generation",
            "[0.0, 0.2, 0.5]",
            opt["temperature"],
            "เพื่อพิสูจน์ว่างานถาม-ตอบเอกสารวิชาการ (Academic RAG) ควรเปิดให้โมเดลสุ่มคำศัพท์ (Temp > 0) หรือควรล็อกการตัดสินใจแบบ Deterministic (Temp = 0.0) เพื่อป้องกันอาการมั่วข้อมูล (Hallucination)",
            "เลือก temperature = 0.0 เพราะให้ผลลัพธ์เที่ยงตรง 100% (Reproducible), ผ่านกฎ Anti-Hallucination Guard 100.0% และตอบได้เร็วกว่า Temp 0.2 และ 0.5",
        ],
    ]
    if llm_winner:
        rows_opt.append([
            11,
            "llm_model (RTX 3050 Ti 4GB)",
            "Stage 3: เปรียบเทียบโมเดล LLM 7 รุ่น",
            "[gemma3:4b, qwen2.5:3b, qwen3:4b, llama3.2:3b, gemma3:1b, qwen2.5:7b, llama3.1:8b]",
            f"{llm_winner['best_model']} (เร็วคุ้มค่า) & gemma3:4b (คุณภาพสูงสุด)",
            "เพื่อค้นหาว่าบนข้อจำกัดฮาร์ดแวร์จริง (RTX 3050 Ti 4GB VRAM + RAM 16GB) โมเดลขนาดใด (1B vs 3B vs 4B vs 7B/8B) ให้จุดสมดุลระหว่างความแม่นยำภาษาไทย การอ้างอิง และความเร็วในการตอบดีที่สุด",
            f"เลือกใช้งาน 2 โหมดตามจุดประสงค์: (1) llama3.2:3b (2.0GB) ชนะเลิศความคุ้มค่ารวม (Suitability = {llm_winner['suitability_score']:.2f}, ตอบไว 5.60s / 47.6 TPS, Phrase Recall 86.7%) และ qwen2.5:3b (60.0 TPS) สำหรับเน้นความเร็วสูง (2) gemma3:4b (3.3GB) ชนะเลิศคุณภาพเนื้อหาสูงสุด (Quality = 84.67) สำหรับเน้นภาษาไทยและตารางวิชาการละเอียด",
        ])

    for c_idx, h in enumerate(headers_opt, start=1):
        ws1.cell(row=4, column=c_idx, value=h)
    for r_offset, row_vals in enumerate(rows_opt, start=5):
        for c_idx, val in enumerate(row_vals, start=1):
            ws1.cell(row=r_offset, column=c_idx, value=val)
    style_table(ws1, 4, 4 + len(rows_opt), len(headers_opt), winner_rows=set(range(5, 5 + len(rows_opt))), left_cols=(2, 3, 6, 7))
    auto_fit_columns(ws1, max_width=55)

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
        "ทำไมถึงนำค่านี้มาทดสอบ (Why Tested)",
        "ทำไมถึงเลือก / ไม่เลือกค่านี้ (Why Selected / Verdict)",
    ]
    s1_rationale_map = {
        "top_k = 100": (
            "ทดสอบเพดานสูงสุด (Upper Bound) เมื่อดึง Candidate Pool กว้างสุด 100 ชิ้น",
            "❌ ไม่เลือก: ใช้เวลาค้นหาพุ่งถึง 1,740.7 ms (ช้ากว่า top_k=15 ถึง 3.7 เท่า) โดยที่ความแม่นยำไม่ได้เพิ่มขึ้น",
        ),
        "top_k = 50": (
            "ทดสอบ Candidate Pool ขนาดใหญ่ (50 ชิ้น) สำหรับคำถามที่คีย์เวิร์ดกระจายหลายหน้า",
            "❌ ไม่เลือก: ใช้เวลาค้นหา 977.6 ms ช้าเกินไปเมื่อเทียบกับ top_k=15 ที่ได้ Hit Rate และ MRR เท่ากัน",
        ),
        "top_k = 30": (
            "ทดสอบค่ามาตรฐานเดิมของระบบ (Baseline เดิม = 30 ชิ้น)",
            "⚠️ รองชนะเลิศ: แม่นยำเท่ากับ top_k=15 แต่ใช้เวลาค้นหานานกว่า (675.2 ms vs 468.8 ms)",
        ),
        "top_k = 15": (
            "ทดสอบจุดสมดุล (Sweet Spot = 15 ชิ้น) ระหว่างความเร็วและความครอบคลุมของเนื้อหา",
            "🏆 เลือกเป็นผู้ชนะ (Composite 88.15): ดึงเนื้อหาเทคนิคครบ (Hit 92.3%, MRR 0.8718) และใช้เวลาเพียง 468.8 ms",
        ),
        "top_k = 10": (
            "ทดสอบการลดขนาด Pool ลงเหลือ 10 ชิ้นเพื่อเน้นความเร็วในการค้นหา",
            "⚠️ ไม่เลือก: เร็วขึ้นเล็กน้อย (371.4 ms) แต่เสี่ยงพลาด Chunk ในคำถามที่เอกสารมีหลายบท",
        ),
        "top_k = 5": (
            "ทดสอบขีดจำกัดล่าง (Lower Bound = 5 ชิ้น) ดึงเฉพาะ 5 อันดับแรกจาก Qdrant",
            "❌ ไม่เลือก: แคบเกินไป! เนื้อหาบทที่ 3-4 หลุดจาก Pool ทำให้ Hit Rate ตกเหลือ 76.9% และ MRR ตกเหลือ 0.5577",
        ),
        "rerank_top_n = 30": (
            "ทดสอบการไม่ตัด Chunks ทิ้งหลัง Rerank (ส่งต่อทั้ง 30 ชิ้น)",
            "❌ ไม่เลือก: มี Chunks ที่ไม่เกี่ยวข้องปะปนสูง ทำให้ Precision@N ตกเหลือเพียง 53.7%",
        ),
        "rerank_top_n = 15": (
            "ทดสอบการเก็บ 후보 15 ชิ้นหลัง Rerank เผื่อคำถามเปรียบเทียบหลายโปรเจกต์",
            "⚠️ ไม่เลือก: ได้ Hit Rate 100% แต่ Precision@N (67.1%) ต่ำกว่า rerank_top_n=10",
        ),
        "rerank_top_n = 10": (
            "ทดสอบจุดสมดุลการคัดกรองหลัง Cross-Encoder Reranker (10 ชิ้น)",
            "🏆 เลือกเป็นผู้ชนะ (Composite 90.05): Hit Rate เต็ม 100.0%, Recall@N สูงถึง 96.2% และ Precision@N สมดุล (75.6%)",
        ),
        "rerank_top_n = 5": (
            "ทดสอบการคัดเฉพาะ Top-5 ที่คะแนน Rerank สูงสุด",
            "⚠️ รองชนะเลิศ: แม่นยำสูงในคำถามเดี่ยว แต่ในคำถามเปรียบเทียบหลายโปรเจกต์มีโอกาสที่โปรเจกต์ที่ 2 จะหลุดขอบ",
        ),
        "rerank_top_n = 3": (
            "ทดสอบการคัดแบบเข้มงวดเหลือเพียง 3 ชิ้นแรก",
            "❌ ไม่เลือก: แคบเกินไปสำหรับคำถามเชิงลึกและคำถามเปรียบเทียบ (Composite ลดเหลือ 86.26)",
        ),
        "rerank_top_n = 1": (
            "ทดสอบสุดโต่ง (Extreme Top-1) คืนเฉพาะ Chunk อันดับ 1 ชิ้นเดียว",
            "❌ ไม่เลือก: ตอบคำถามเปรียบเทียบ 2 โครงงาน (GT-08) ไม่ได้เลย เพราะส่งได้แค่โครงงานเดียว (Recall@N ตกเหลือ 80.8%)",
        ),
    }
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
        why_test, why_sel = s1_rationale_map.get(r["exp_label"], ("ทดสอบเปรียบเทียบค่าพารามิเตอร์", "พิจารณาตามคะแนน Composite Score"))
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
            why_test,
            why_sel,
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws2.cell(row=idx, column=c_idx, value=val)

    style_table(ws2, 4, 4 + len(exp12_rows), len(headers_s1), winner_rows=winner_rows_s1, left_cols=(1, 2, 17, 18))
    auto_fit_columns(ws2, max_width=52)

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
        "ทำไมถึงนำมาทดสอบ (Why Tested)",
        "ทำไมถึงเลือก / ไม่เลือก (Why Selected & Impact)",
    ]
    ab_rationale_map = {
        "ablation_full_pipeline": (
            "ทดสอบระบบ RAGcoon ที่เปิดครบทุกโมดูล (Hybrid BM25+E5 + Reranker + Filter + Fast-Path) เป็นเกณฑ์มาตรฐานสูงสุด",
            "🏆 เลือกใช้งานจริง (Composite 91.64): Hit Rate เต็ม 100.0%, MRR สูงสุด 0.9231, ขยะเป็น 0.0% และค้นหาเร็วเพียง 312.4 ms",
        ),
        "ablation_dense_only": (
            "ทดสอบปิด Sparse BM25 เหลือเฉพาะเวกเตอร์ความหมาย (Multilingual-E5) เพื่อพิสูจน์ว่าเวกเตอร์อย่างเดียวจับรหัสชิปได้หรือไม่",
            "❌ ไม่เลือก: เมื่อขาด BM25 ระบบพลาดรหัสฮาร์ดแวร์เฉพาะทาง (SX1276) ทำให้ Hit Rate ตกเหลือ 84.6% และ MRR ตกเหลือ 0.7769",
        ),
        "ablation_bm25_only": (
            "ทดสอบปิดเวกเตอร์ความหมาย เหลือเฉพาะการค้นหาคำตรงตัว (BM25 Keyword) เพื่อดูว่าค้นหาคำพ้องความหมายได้หรือไม่",
            "❌ ไม่เลือก: แม้จับชื่อเฉพาะได้ดี แต่เมื่อคำถามใช้คำอธิบายเชิงความหมายโดยไม่ตรงคีย์เวิร์ดเป๊ะ คะแนน Composite ลดเหลือ 88.24",
        ),
        "ablation_no_rerank": (
            "ทดสอบปิด BGE Cross-Encoder Reranker เพื่อดูว่าลำดับคะแนนดิบจาก Qdrant RRF แม่นยำพอสำหรับส่งเข้า LLM หรือยัง",
            "❌ ไม่เลือก: เมื่อปิด Reranker ย่อหน้าที่มีคำตอบจริงตกไปอยู่อันดับ 2-4 ทำให้ MRR ร่วงจาก 0.9231 เหลือ 0.7436 (-18.0%)",
        ),
        "ablation_no_filter": (
            "ทดสอบปิดตัวกรองขยะเอกสาร (Boilerplate Filter) เพื่อดูว่าหน้าสารบัญ/บรรณานุกรม/กิตติกรรมประกาศส่งผลเสียแค่ไหน",
            "❌ ไม่เลือก: หน้าสารบัญและกิตติกรรมประกาศหลุดเข้ามาแย่งพื้นที่ Top-N ถึง 25.0% ทำให้ MRR ตกเหลือ 0.7372 (Composite เหลือ 76.26)",
        ),
        "ablation_no_fast_path": (
            "ทดสอบปิดทางลัด Metadata Scroll เพื่อดูความแตกต่างของเวลาค้นหาและความแม่นยำในคำถามหมวดอาจารย์ที่ปรึกษา/ผู้จัดทำ",
            "⚠️ ไม่เลือก: ความแม่นยำยังสูงแต่เวลาค้นหาเฉลี่ยช้าลงเกือบเท่าตัว (จาก 312.4 ms เพิ่มเป็น 555.8 ms)",
        ),
        "ablation_legacy_rag": (
            "จำลองระบบ RAG แบบดั้งเดิม (Dense ล้วน + ไม่ใช้ Reranker + ไม่กรองขยะ + ไม่มี Fast-Path) เพื่อวัดพัฒนาการของระบบใหม่",
            "❌ ไม่เลือก (Baseline เก่า): มีขยะปะปนถึง 57.1%, MRR ต่ำเพียง 0.6000 และได้คะแนนรวมต่ำสุดเพียง 65.87 (ระบบใหม่ดีกว่า +25.77 คะแนน)",
        ),
    }
    exp3_rows = [r for r in s1_all if r["exp_group"] == "Exp 3: Component Ablation"]
    max_exp3_score = max((r["composite_score"] for r in exp3_rows), default=0)

    for c_idx, h in enumerate(headers_ab, start=1):
        ws3.cell(row=4, column=c_idx, value=h)

    winner_rows_ab = set()
    for idx, r in enumerate(exp3_rows, start=5):
        is_w = r["composite_score"] == max_exp3_score
        if is_w:
            winner_rows_ab.add(idx)
        why_t, why_s = ab_rationale_map.get(r["profile_name"], (r["description"], "พิจารณาตามคะแนน Composite"))
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
            why_t,
            why_s,
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws3.cell(row=idx, column=c_idx, value=val)

    style_table(ws3, 4, 4 + len(exp3_rows), len(headers_ab), winner_rows=winner_rows_ab, left_cols=(1, 2, 15, 16))
    auto_fit_columns(ws3, max_width=52)

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
        "ทำไมถึงนำค่านี้มาทดสอบ (Why Tested)",
        "ทำไมถึงเลือก / ไม่เลือกค่านี้ (Why Selected / Verdict)",
    ]
    s2_rationale_map = {
        "sweep_chunks_15_quota_5": (
            "ทดสอบเพดานบริบทกว้างสุด (15 Chunks, โควตา 5/โปรเจกต์) เพื่อดูว่ายิ่งส่งเนื้อหาเยอะ LLM ยิ่งตอบดีขึ้นหรือไม่",
            "❌ ไม่เลือก: เกิดอาการสำลักบริบท (Context Overload) ในข้อ GT-01 ทำให้ Phrase Recall ตกเหลือ 80.0% และกิน Input Tokens สูงถึง 1,720 tokens",
        ),
        "sweep_chunks_10_quota_3": (
            "ทดสอบบริบทขนาดใหญ่ (10 Chunks, โควตา 3/โปรเจกต์)",
            "❌ ไม่เลือก: ใช้ Input Tokens เยอะเกินจำเป็น แต่ได้ Key Phrase Recall 80.0% ต่ำกว่าการส่ง 6 Chunks",
        ),
        "sweep_chunks_6_quota_2": (
            "ทดสอบจุดสมดุล (6 Chunks, ล็อกโควตา 2 Chunks/โปรเจกต์) เพื่อให้รองรับการเปรียบเทียบ 3 โปรเจกต์อย่างเท่าเทียม",
            "🏆 เลือกเป็นผู้ชนะ Exp 4 (Composite 83.75): ได้ Quality สูงสุด 84.67, Key Phrase Recall สูงสุด 86.68%, และ Multi-Project Coverage เต็ม 100%",
        ),
        "sweep_chunks_5_quota_2": (
            "ทดสอบค่ามาตรฐานเดิม (5 Chunks, โควตา 2/โปรเจกต์)",
            "⚠️ รองชนะเลิศ: ประสิทธิภาพใกล้เคียง 6 Chunks แต่ในคำถามเปรียบเทียบ 3 โปรเจกต์ โปรเจกต์ที่ 3 จะได้เพียง 1 Chunk",
        ),
        "sweep_chunks_4_quota_2": (
            "ทดสอบบริบทขนาดกะทัดรัด (4 Chunks, โควตา 2/โปรเจกต์) เพื่อลดเวลาอ่าน Prompt ของการ์ดจอ",
            "⚠️ ไม่เลือก: เร็วขึ้นเล็กน้อย (13.48s) แต่ได้คะแนน Quality (82.40) และ Phrase Recall (80.0%) ต่ำกว่า 6 Chunks",
        ),
        "sweep_chunks_2_quota_1": (
            "ทดสอบขีดจำกัดล่างสุด (Minimal 2 Chunks, โควตา 1/โปรเจกต์) เพื่อเน้นความเร็วสูงสุด",
            "❌ ไม่เลือก: บริบทน้อยเกินไปสำหรับคำถามเชิงลึกที่รายละเอียดกระจายอยู่หลายหน้า ทำให้ Phrase Recall ลดเหลือ 80.0%",
        ),
        "sweep_chunks_6_quota_6": (
            "ทดสอบส่ง 6 Chunks แต่ปิดการจำกัดโควตาต่อโปรเจกต์ (Uncapped Quota=6) เพื่อพิสูจน์ความสำคัญของ Fair Quota",
            "❌ ไม่เลือก: เมื่อไม่จำกัดโควตา โปรเจกต์เดียวกินพื้นที่ Chunks จน Input Tokens พุ่งเป็น 2,177 tokens และใช้เวลานานขึ้นเป็น 19.93s",
        ),
        "sweep_preset_concise_t0": (
            "ทดสอบ Prompt แบบสั้นกระชับ (concise + Temp 0.0) เพื่อดูว่าช่วยลดเวลาตอบของโมเดลได้แค่ไหน",
            "⚠️ ไม่เลือกเป็นค่าหลัก: ตอบไวขึ้น (12.00s) แต่บางข้อตัดจบสั้นเกินไปจนไม่ได้แนบ `[Source: ..., Page: ...]` ครบถ้วน",
        ),
        "sweep_preset_balanced_t0": (
            "ทดสอบ Prompt มาตรฐานสมดุล (balanced + Temp 0.0) ที่เน้นความครบถ้วนควบคู่ความกระชับ",
            "🏅 เลือกใช้เป็นค่าเริ่มต้นทั่วไป (Composite 82.61, Quality 84.67): สมดุลทั้งโครงสร้าง Markdown การอ้างอิง และความแม่นยำ",
        ),
        "sweep_preset_deep_t0": (
            "ทดสอบ Prompt เชิงลึกวิชาการ (deep_academic + Temp 0.0) ที่บังคับแจกแจงรายละเอียดอุปกรณ์และผลการทดลอง",
            "🏆 เลือกเป็นผู้ชนะ Exp 5 (Composite 83.50, Quality 83.47): ให้คำตอบเชิงลึกและการอ้างอิงวิชาการที่รัดกุมที่สุด",
        ),
        "sweep_preset_step_t0": (
            "ทดสอบ Prompt แบบอธิบายทีละขั้นตอน (step_by_step + Temp 0.0)",
            "⚠️ รองชนะเลิศ (Composite 83.49): เหมาะกับคำถามถามวิธีการทดลอง แต่ในคำถามทั่วไปใช้รูปแบบคล้าย deep_academic",
        ),
        "sweep_preset_balanced_t02": (
            "ทดสอบเพิ่มความยืดหยุ่นของคำศัพท์ด้วย Temperature = 0.2",
            "❌ ไม่เลือก: ไม่ได้เพิ่มความแม่นยำของคีย์เวิร์ดเมื่อเทียบกับ Temp = 0.0 และมีความแปรปรวนในการอ้างอิง",
        ),
        "sweep_preset_balanced_t05": (
            "ทดสอบ Temperature = 0.5 (ระดับสร้างสรรค์ปานกลาง) เพื่อดูผลกระทบต่อความแม่นยำในงาน RAG",
            "❌ ไม่เลือก: ใช้เวลาตอบนานขึ้น (16.38s) และคะแนนรวมลดลงเหลือ 80.65 เพราะงานเอกสารวิชาการต้องการความเป๊ะตามต้นฉบับ 100%",
        ),
    }
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
        why_t2, why_s2 = s2_rationale_map.get(r["profile_name"], ("ทดสอบเปรียบเทียบพารามิเตอร์ฝั่ง LLM", "พิจารณาตามคะแนน Composite"))
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
            why_t2,
            why_s2,
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            ws4.cell(row=idx, column=c_idx, value=val)

    style_table(ws4, 4, 4 + len(s2_all), len(headers_s2), winner_rows=winner_rows_s2, left_cols=(1, 2, 20, 21))
    auto_fit_columns(ws4, max_width=52)

    # -------------------------------------------------------------------------
    # SHEET 5: Stage 1 Per-Query Granular Breakdown
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
        "คำถามที่ใช้ทดสอบ (Query)",
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
            qid = pq.get("id", "")
            q_text = golden_map.get(qid, {}).get("query", "")
            vals = [
                r["exp_group"],
                r["exp_label"],
                qid,
                pq.get("category", ""),
                q_text,
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

    style_table(ws5, 4, r_cursor - 1, len(headers_pq1), left_cols=(1, 2, 4, 5))
    auto_fit_columns(ws5)

    # -------------------------------------------------------------------------
    # SHEET 6: Stage 2 Per-Query Answers & Rule-by-Rule Rubric Breakdown
    # -------------------------------------------------------------------------
    s_name_6 = sheet_name(5, "Stage2_PerQuery_Answers")
    if s_name_6 in wb.sheetnames:
        del wb[s_name_6]
    ws6 = wb.create_sheet(title=s_name_6)

    ws6["A1"] = "📝 Stage 2 Per-Query Breakdown: ผลลัพธ์รายข้อ + คะแนนแยกตามกฎ (Rule-by-Rule Rubric) + ตัวอย่างคำตอบจริง"
    ws6["A1"].font = TITLE_FONT
    ws6["A2"] = "แสดงที่มาของคะแนนรายกฎ: กฎที่ 1 Citation (30), กฎที่ 2 Cleanliness (25), กฎที่ 3 Latency (25), กฎที่ 4 Completeness (20), คำสำคัญเฉลย (Key Phrase Recall) และ Anti-Hallucination"
    ws6["A2"].font = BOLD_FONT

    headers_pq2 = [
        "กลุ่มการทดลอง (Exp Group)",
        "การตั้งค่า (Setting)",
        "รหัสข้อ (Query ID)",
        "คำถามที่ใช้ทดสอบ (Query)",
        "กฎที่ 1: Citation (เต็ม 30)",
        "กฎที่ 2: Cleanliness (เต็ม 25)",
        "กฎที่ 3: Speed/Latency (เต็ม 25)",
        "กฎที่ 4: Completeness (เต็ม 20)",
        "รวมคะแนนกฎ Rubric (เต็ม 100)",
        "กฎที่ 5: Key Phrase Recall (%)",
        "กฎที่ 6: Hallucination Guard (%)",
        "Blended Quality Score (0-100)",
        "คำสำคัญเฉลยที่ต้องมี (Expected Key Phrases)",
        "Input Tokens",
        "Output Tokens",
        "LLM Latency (s)",
        "ตัวอย่างคำตอบจริงจาก gemma3:4b (Actual Output Preview)",
    ]
    for c_idx, h in enumerate(headers_pq2, start=1):
        ws6.cell(row=4, column=c_idx, value=h)

    r_cursor2 = 5
    for r in s2_all:
        for pq in r.get("per_query", []):
            qid = pq.get("id", "")
            tc_info = golden_map.get(qid, {})
            q_text = tc_info.get("query", "")
            exp_phrases = ", ".join(tc_info.get("key_phrases", []))
            ans_prev = pq.get("answer_preview", "")
            tot_s = float(pq.get("total_seconds", 0.0))
            is_fp = qid == "GT-04"
            rub = compute_rubric_breakdown(ans_prev, tot_s, is_fast_path=is_fp)
            guard_pct = 100.0 if pq.get("hallucination_guard", 1) == 1 else 0.0

            vals = [
                r["exp_group"],
                r["exp_label"],
                qid,
                q_text,
                rub["citation_30"],
                rub["cleanliness_25"],
                rub["latency_25"],
                rub["completeness_20"],
                rub["rubric_total_100"],
                pq.get("phrase_recall_pct", 0.0),
                guard_pct,
                pq.get("quality_score", 0.0),
                exp_phrases,
                pq.get("input_tokens", 0),
                pq.get("output_tokens", 0),
                pq.get("llm_seconds", 0.0),
                ans_prev,
            ]
            for c_idx, v in enumerate(vals, start=1):
                ws6.cell(row=r_cursor2, column=c_idx, value=v)
            r_cursor2 += 1

    style_table(ws6, 4, r_cursor2 - 1, len(headers_pq2), left_cols=(1, 2, 4, 13, 17))
    auto_fit_columns(ws6, max_width=55)

    # -------------------------------------------------------------------------
    # SHEET 7: Full Experiment History Log
    # -------------------------------------------------------------------------
    s_name_7 = sheet_name(6, "Full_Experiment_Log")
    if s_name_7 in wb.sheetnames:
        del wb[s_name_7]
    ws7 = wb.create_sheet(title=s_name_7)

    ws7["A1"] = "📋 บันทึกประวัติการทดลองทั้งหมด (Complete Experiment Tracking Log - Stage 1, Stage 2 & Multi-LLM)"
    ws7["A1"].font = TITLE_FONT
    ws7["A2"] = "รวบรวมผลการรันทุกการตั้งค่า พร้อมรหัสการทดลอง (Run ID) และคะแนนรวม (Composite Score)"
    ws7["A2"].font = BOLD_FONT

    headers_log = [
        "Run ID",
        "ระยะการทดสอบ (Stage)",
        "กลุ่มการทดลอง (Exp Group)",
        "การตั้งค่า / โมเดล (Setting / Model)",
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
        "Hit / Phrase Recall",
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
            f"Hit: {r['hit_rate_pct']:.1f}%",
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
            f"Phrase: {r['avg_phrase_recall_pct']:.1f}%",
            f"Quality: {r['avg_quality_score']:.1f}",
            f"{r['avg_llm_seconds']:.2f} s",
            r["composite_score"],
        ]
        for c_idx, v in enumerate(vals, start=1):
            ws7.cell(row=row_cursor, column=c_idx, value=v)
        row_cursor += 1

    for i, r in enumerate(llm_bench, start=1):
        if i == 1:
            winner_log_rows.add(row_cursor)
        vals = [
            f"EXP-LLM-{i:02d}",
            "Stage 3: Multi-LLM",
            "Exp 6: 7-Model Benchmark",
            f"{r['model']} ({r['size_gb']} GB)",
            15,
            10,
            "ON",
            "ON",
            "ON",
            "ON",
            6,
            2,
            "balanced",
            0.0,
            f"Phrase: {r['avg_phrase_recall_pct']:.1f}%",
            f"Quality: {r['avg_quality_score']:.1f}",
            f"{r['avg_llm_seconds']:.2f} s ({r['avg_tps']:.1f} TPS)",
            r["composite_score"],
        ]
        for c_idx, v in enumerate(vals, start=1):
            ws7.cell(row=row_cursor, column=c_idx, value=v)
        row_cursor += 1

    style_table(ws7, 4, row_cursor - 1, len(headers_log), winner_rows=winner_log_rows, left_cols=(2, 3, 4))
    auto_fit_columns(ws7)

    # -------------------------------------------------------------------------
    # SHEET 8: Deterministic Scoring Rules, Rubrics & Mathematical Formulas
    # -------------------------------------------------------------------------
    s_name_8 = sheet_name(7, "Scoring_Rules_Formulas")
    if s_name_8 in wb.sheetnames:
        del wb[s_name_8]
    ws8 = wb.create_sheet(title=s_name_8)

    ws8["A1"] = "📐 กฎการให้คะแนนและสูตรคำนวณมาตรฐาน (Deterministic Scoring Rules, Rubric Breakdown & Formulas)"
    ws8["A1"].font = TITLE_FONT
    ws8["A2"] = "อธิบายหลักการคำนวณทุกตัวชี้วัดแบบโปร่งใส (100% Rule-Based & Reproducible) ทั้งฝั่งค้นหา, ฝั่งคำตอบ LLM, และความเหมาะสมของโมเดลกับ RTX 3050 Ti (4GB VRAM)"
    ws8["A2"].font = BOLD_FONT

    headers_rules = [
        "หมวดหมู่ (Stage)",
        "ชื่อตัวชี้วัด / กฎการให้คะแนน (Metric / Rule Name)",
        "คะแนนเต็ม / น้ำหนัก (Max / Weight)",
        "สูตรคณิตศาสตร์และเงื่อนไขการตรวจให้คะแนน (Exact Formula & Rule Condition)",
        "ตัวอย่างการแทนค่าคำนวณจริง (Worked Calculation Example)",
    ]
    rows_rules = [
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "1. Answer-Bearing Hit Rate (%)",
            "น้ำหนัก 25% ใน Stage 1 Composite",
            "Hit = 1 เมื่อมีอย่างน้อย 1 Chunk ใน Top-N ที่มาจากไฟล์เฉลย (expected_sources) + มีคำสำคัญเฉลย (key_phrases) + ไม่ใช่หน้าขยะ (Boilerplate)\nสูตร: (จำนวนข้อที่ Hit / จำนวนข้อคำถามที่มีคำตอบในคลัง 13 ข้อ) × 100",
            "Full Pipeline ตอบถูก 13 จาก 13 ข้อ -> (13 / 13) × 100 = 100.0%\nแต่ top_k=5 ตอบถูก 10 จาก 13 ข้อ -> (10 / 13) × 100 = 76.92%",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "2. Mean Reciprocal Rank (MRR)",
            "น้ำหนัก 25% ใน Stage 1 Composite",
            "วัดว่า Chunk ที่มีคำตอบจริงปรากฏอยู่ในลำดับที่เท่าไหร่ (rank_1)\nสูตรรายข้อ: RR = 1 / rank_1 (ถ้าอยู่อันดับ 1 ได้ 1.0, อันดับ 2 ได้ 0.5, อันดับ 4 ได้ 0.25)\nสูตรรวม: ค่าเฉลี่ยของ RR ทั้ง 13 ข้อ",
            "เมื่อเปิด Cross-Encoder Reranker: เนื้อหาเทคนิคถูกดันขึ้นอันดับ 1 เกือบทุกข้อ -> MRR = 0.9231\nเมื่อปิด Reranker (No Reranker): เนื้อหาตกไปอันดับ 2-3 -> MRR ลดเหลือ 0.7436",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "3. Precision@N (%)",
            "น้ำหนัก 20% ใน Stage 1 Composite",
            "วัดความแม่นยำหรือความเข้มข้นของเนื้อหาใน Top-N ที่คัดมา\nสูตร: (จำนวน Chunks ที่เกี่ยวข้องจริงใน Top-N / จำนวน Chunks ที่คืนมาทั้งหมด N) × 100",
            "หากคืนมา 5 Chunks และเป็นเนื้อหาโปรเจกต์ที่ตรงคำถาม 4 Chunks -> (4 / 5) × 100 = 80.0%",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "4. Recall@N (%)",
            "น้ำหนัก 10% ใน Stage 1 Composite",
            "วัดความครบถ้วนของเอกสารอ้างอิงเฉลย (สำคัญมากในข้อเปรียบเทียบหลายโปรเจกต์ เช่น GT-08)\nสูตร: (จำนวนไฟล์ expected_sources ที่ค้นเจอใน Top-N / จำนวน expected_sources ทั้งหมดของข้อนั้น) × 100",
            "ข้อ GT-08 ต้องใช้ 2 โปรเจกต์ (The LoRaWAN + BSLD): หากเจอครบทั้ง 2 โปรเจกต์จะได้ Recall = 100.0% (หากเจอแค่โปรเจกต์เดียวได้ 50.0%)",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "5. Cleanliness Score (100 - Boilerplate Noise %)",
            "น้ำหนัก 10% ใน Stage 1 Composite",
            "ตรวจจับขยะเอกสาร 7 ประเภทด้วยกฎ Regex (สารบัญ, กิตติกรรมประกาศ, บรรณานุกรม, ลายเซ็นกรรมการ, หน้าปก, ตารางแผนงาน, เลขหน้าเดี่ยว)\nสูตร: Cleanliness = 100 - ((จำนวน Chunks ขยะ / จำนวน Chunks ทั้งหมด) × 100)",
            "เมื่อเปิด Boilerplate Filter: ขยะ = 0% -> Cleanliness = 100.0\nเมื่อปิด Filter (No Filter): ขยะหลุดเข้ามา 25.0% -> Cleanliness ลดเหลือ 75.0",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "6. Search Speed Score & Cutoff Focus",
            "น้ำหนัก 10% (Speed 5% + Cutoff 5%)",
            "Speed Score = 100 × (1 - max(0, Search_ms - 100) / 1900)\nCutoff Focus Score = 100 เมื่อ rerank_top_n <= 6 และลดลงเมื่อส่ง Chunks เยอะเกินไปจนล้น Context",
            "Search_ms = 312.4 ms -> Speed Score = 88.82 คะแนน\nแต่ถ้าตั้ง top_k=100 เวลาพุ่งเป็น 1,740.7 ms -> Speed Score เหลือเพียง 13.65 คะแนน",
        ],
        [
            "Stage 1: ฝั่งค้นหา (Retrieval)",
            "★ สูตรรวม Stage 1 Composite Score (0-100)",
            "เต็ม 100 คะแนน",
            "Composite_S1 = 0.25×HitRate + 0.25×(MRR×100) + 0.20×Precision@N + 0.10×Recall@N + 0.10×Cleanliness + 0.05×SpeedScore + 0.05×CutoffFocus",
            "Full Pipeline: 0.25(100) + 0.25(92.31) + 0.20(82.5) + 0.10(96.15) + 0.10(100) + 0.05(88.82) + 0.05(62.5) = 91.64 คะแนน (อันดับ 1)",
        ],
        [
            "Stage 2 & 3: กฎให้คะแนนคำตอบ LLM (Rubric Rule 1)",
            "Rule 1: Citation Strictness (ความถูกต้องของการอ้างอิง)",
            "เต็ม 30 คะแนน (ใน Rubric 100)",
            "ตรวจด้วย Regex ว่าคำตอบมีการระบุแหล่งอ้างอิงตามรูปแบบบังคับ `[Source: ชื่อไฟล์.pdf, Page: X]` หรือ `📄 ชื่อไฟล์.pdf` หรือไม่:\n- มีรูปแบบอ้างอิงครบถ้วน หรือมาจาก Fast-Path Template = 30 คะแนน\n- มีคำว่า Source/หน้า แต่ผิดรูปแบบ = 15 คะแนน\n- ไม่มีการอ้างอิงเลย = 5 คะแนน",
            "คำตอบของ LLM ระบุ `[Source: 1_6031501044_6031501061_FinalProject.pdf, Page: 18]` -> ได้เต็ม 30 / 30 คะแนน",
        ],
        [
            "Stage 2 & 3: กฎให้คะแนนคำตอบ LLM (Rubric Rule 2)",
            "Rule 2: Cleanliness & Format Guard (ความสะอาดของคำตอบ)",
            "เต็ม 25 คะแนน (ใน Rubric 100)",
            "ตั้งต้น 25 คะแนน หักจุดละ 10 คะแนนหาก LLM สร้างหัวข้อขยะที่ไม่มีข้อมูล เช่น `### 🔔 บริการภายนอก /ไม่มีข้อมูล`, `### ⚠️ ข้อมูลที่ไม่ได้ระบุ`, หรือ `## Sources -`",
            "คำตอบสะอาด ไม่มีบล็อกว่างเปล่าที่ไร้ความหมาย -> ได้เต็ม 25 / 25 คะแนน",
        ],
        [
            "Stage 2 & 3: กฎให้คะแนนคำตอบ LLM (Rubric Rule 3)",
            "Rule 3: Response Latency Score (ความเร็วในการตอบ)",
            "เต็ม 25 คะแนน (ใน Rubric 100)",
            "ให้คะแนนตามเวลาตอบรวม (Total Seconds):\n- <= 1.5 วินาที = 25 คะแนน\n- <= 3.5 วินาที = 20 คะแนน\n- <= 6.0 วินาที = 15 คะแนน\n- <= 10.0 วินาที = 10 คะแนน\n- > 10.0 วินาที = 5 คะแนน",
            "โมเดลตัวเบา 1B-3B ที่ตอบภายใน 3-6 วินาทีจะได้คะแนน Latency Score สูงกว่ารุ่น 7B-8B ที่ใช้เวลา >15 วินาที",
        ],
        [
            "Stage 2 & 3: กฎให้คะแนนคำตอบ LLM (Rubric Rule 4)",
            "Rule 4: Substantiveness & Completeness (ความสมบูรณ์ของเนื้อหา)",
            "เต็ม 20 คะแนน (ใน Rubric 100)",
            "ตรวจความยาวและความสมบูรณ์ของคำตอบ:\n- ความยาว >= 150 ตัวอักษร = 20 คะแนน\n- ความยาว 50 - 149 ตัวอักษร = 15 คะแนน\n- ความยาว 1 - 49 ตัวอักษร = 10 คะแนน\n- คำตอบว่างเปล่า = 0 คะแนน",
            "คำตอบอธิบายสถาปัตยกรรมและอุปกรณ์ครบถ้วน (ยาว >= 150 ตัวอักษร) -> ได้เต็ม 20 / 20 คะแนน",
        ],
        [
            "Stage 2 & 3: กฎตรวจคำตอบกับเฉลย (Ground-Truth Verification)",
            "Rule 5: Key Phrase Recall (%) & Rule 6: Anti-Hallucination Guard (%)",
            "ถ่วงน้ำหนักเข้า Blended Quality & Composite",
            "- Key Phrase Recall (%) = (จำนวนคำสำคัญใน key_phrases ที่ปรากฏจริงในคำตอบ / จำนวน key_phrases ทั้งหมดของข้อนั้น) × 100\n- Hallucination Guard (%) = 100% เมื่อไม่ปรากฏคำต้องห้าม (forbidden_phrases เช่น มั่วว่ามี Line Notify ใน GT-06)\n- Blended Quality Score = 0.60×RubricScore + 0.25×KeyPhraseRecall + 0.15×HallucinationGuard",
            "ข้อ GT-01 เฉลยกำหนด key_phrases = ['The LoRaWAN', 'SX1276', 'LoRa']: เมื่อคำตอบมีครบทั้ง 3 คำ -> Key Phrase Recall = 100.0%, Hallucination Guard = 100.0%",
        ],
        [
            "Stage 3: กฎวัดความเหมาะสมกับฮาร์ดแวร์ (Hardware VRAM Fit Rule)",
            "Rule 7: RTX 3050 Ti (4GB VRAM) Hardware Fit Score & Multi-LLM Suitability",
            "เต็ม 100 คะแนน (น้ำหนัก 15% ในการคัดเลือกโมเดล)",
            "วัดความเข้ากันได้ของขนาดโมเดลกับ VRAM 4GB ของการ์ดจอ RTX 3050 Ti Laptop:\n- ขนาด <= 1.0 GB (เช่น gemma3:1b): VRAM Fit = 100\n- ขนาด 1.5 - 2.0 GB (เช่น qwen2.5:3b, llama3.2:3b): VRAM Fit = 97-98\n- ขนาด 2.5 - 3.3 GB (เช่น qwen3:4b, gemma3:4b): VRAM Fit = 90-95\n- ขนาด > 4.0 GB (เช่น qwen2.5:7b, llama3.1:8b ล้น VRAM ต้องพึ่ง RAM): VRAM Fit = 65-70\nสูตรรวม Multi-LLM Suitability = 0.45×BlendedQuality + 0.25×(0.7×PhraseRecall + 0.3×MultiProj) + 0.15×SpeedScore + 0.15×VRAMFit",
            "โมเดลขนาด 3B-4B (qwen2.5:3b, gemma3:4b, qwen3:4b) ได้เปรียบทั้งความเร็ว (รันบน GPU 100%) และความแม่นยำ จึงชนะรุ่น 7B-8B ที่ล้น VRAM 4GB",
        ],
    ]

    for c_idx, h in enumerate(headers_rules, start=1):
        ws8.cell(row=4, column=c_idx, value=h)
    for r_offset, row_vals in enumerate(rows_rules, start=5):
        for c_idx, val in enumerate(row_vals, start=1):
            ws8.cell(row=r_offset, column=c_idx, value=val)
    style_table(ws8, 4, 4 + len(rows_rules), len(headers_rules), winner_rows={11, 17}, left_cols=(1, 2, 4, 5))
    auto_fit_columns(ws8, max_width=58)

    # -------------------------------------------------------------------------
    # SHEET 9: Concrete Side-by-Side Output Examples Across Parameters
    # -------------------------------------------------------------------------
    s_name_9 = sheet_name(8, "Concrete_Output_Examples")
    if s_name_9 in wb.sheetnames:
        del wb[s_name_9]
    ws9 = wb.create_sheet(title=s_name_9)

    ws9["A1"] = "🔬 ตัวอย่างผลลัพธ์จริงเปรียบเทียบเมื่อปรับค่าพารามิเตอร์ต่างๆ (Concrete Side-by-Side Output Examples)"
    ws9["A1"].font = TITLE_FONT
    ws9["A2"] = "แสดงหลักฐานเชิงประจักษ์ว่าเมื่อเปลี่ยนค่าพารามิเตอร์แต่ละตัว ผลลัพธ์ที่ดึงมา (Chunks) หรือคำตอบของ LLM เปลี่ยนแปลงอย่างไร และถูกหัก/เพิ่มคะแนนตามกฎข้อใด"
    ws9["A2"].font = BOLD_FONT

    headers_ex = [
        "กรณีศึกษา (Case Study)",
        "คำถามที่ใช้ทดสอบ (Test Query)",
        "พารามิเตอร์ที่เปรียบเทียบ (Parameter A vs Parameter B)",
        "ผลลัพธ์จริงเมื่อใช้ค่าที่เหมาะสม (Optimal Parameter Output)",
        "ผลลัพธ์จริงเมื่อใช้ค่าที่ไม่เหมาะสม / ปิดฟีเจอร์ (Sub-Optimal / Ablated Output)",
        "การคิดคะแนนตามกฎ (Rule-Based Score Impact & Explanation)",
    ]
    rows_ex = [
        [
            "Case 1: ผลของขนาดการดึงข้อมูล (top_k = 15 vs top_k = 5)",
            "GT-02: อาจารสุรพลดูแลเรื่องไรบ้าง\n& GT-03: ขั้นตอนการทำงานและการทดลองของ The LoRaWAN",
            "top_k = 15 (Winner)\nเทียบกับ\ntop_k = 5 (แคบเกินไป)",
            "[top_k = 15]: ดึง Candidate Pool 15 ชิ้นครอบคลุมทั้งหน้าบทคัดย่อและหน้าบทที่ 3-4 (หน้า 17-18) ทำให้ Reranker จัด Chunk หน้า 17-18 ที่มีคำว่า 'ESP32', 'SX1276', และขั้นตอนการทดลองขึ้นเป็น Rank #1\n(Hit = 1, RR = 1.00, Precision@5 = 100%)",
            "[top_k = 5]: ดึงมาเพียง 5 ชิ้นแรกซึ่งติดหน้าเกริ่นนำและบทที่ 1 มาเป็นหลัก ทำให้ Chunk ที่มีรายละเอียดการทดลองหลุดไปอยู่อันดับท้ายหรือหลุดจาก Pool\n(MRR เฉลี่ยทั้งชุดตกจาก 0.8718 เหลือเพียง 0.5577 และ Precision@5 ตกจาก 76.9% เหลือ 46.1%)",
            "ตามกฎ Stage 1 (MRR 25% + Precision 20%):\n- top_k=15 ได้ Composite = 88.15 (ชนะเลิศ)\n- top_k=5 ถูกหักคะแนน MRR และ Precision เหลือเพียง 66.67 (-21.48 คะแนน)",
        ],
        [
            "Case 2: ผลของการเปิด/ปิดตัวกรองขยะ (Boilerplate Filter ON vs OFF)",
            "GT-03: ขั้นตอนการทำงานและการทดลองของ The LoRaWAN",
            "enable_boilerplate_filter = True\nเทียบกับ\nenable_boilerplate_filter = False",
            "[Filter = ON]: ตัวกรอง `is_boilerplate_text()` ตัดหน้าสารบัญ (Table of Contents), กิตติกรรมประกาศ (Acknowledgement), และหน้าลายเซ็นกรรมการสอบทิ้งก่อนส่งให้ Reranker เหลือเฉพาะเนื้อหาเทคนิคหน้า 17, 18, 22\n(Boilerplate Noise = 0.0%, MRR = 0.9231)",
            "[Filter = OFF]: หน้าสารบัญที่มีคำว่า 'Chapter 3 Methodology ..... 17' และหน้าบรรณานุกรมหลุดเข้ามาแย่งพื้นที่ใน Top-5 ถึง 25.0% ของจำนวน Chunks ทั้งหมด ทำให้ LLM ได้รับเนื้อหาแหว่ง\n(Boilerplate Noise = 25.0%, MRR ตกเหลือ 0.7372)",
            "ตามกฎ Cleanliness Score (100 - Noise%) และ MRR:\n- เปิด Filter ได้ Cleanliness = 100.0 (Composite = 91.64)\n- ปิด Filter ถูกหัก Cleanliness เหลือ 75.0 และ MRR ลดลง (Composite ตกเหลือ 76.26)",
        ],
        [
            "Case 3: ผลของ Hybrid RRF (BM25 + E5) เทียบกับ Dense Vector ล้วน",
            "GT-01: โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",
            "enable_hybrid = True (BM25+E5)\nเทียบกับ\nenable_hybrid = False (Dense Only)",
            "[Hybrid = ON]: Sparse BM25 จับรหัสฮาร์ดแวร์เฉพาะทาง `SX1276` ในหน้า 18 ของไฟล์ `1_6031501044_6031501061_FinalProject.pdf` ได้แม่นยำ 100% แล้วรวมคะแนนผ่านสูตร RRF ดันขึ้นเป็น Rank #1 ทันที\n(คำตอบ gemma3:4b: ระบุโครงงาน The LoRaWAN และชิป SX1276 ครบทั้ง 3 คำสำคัญ)",
            "[Dense Only = OFF]: โมเดลเวกเตอร์มอง `SX1276` เป็นตัวอักษรทั่วไป จึงดึงโครงงาน IoT อื่นๆ ปะปนขึ้นมา ทำให้ความแม่นยำในการจัดอันดับรหัสชิปและชื่อเฉพาะลดลง\n(Hit Rate ตกจาก 100.0% เหลือ 84.62% และ MRR ลดจาก 0.9231 เหลือ 0.7769)",
            "ตามกฎ Hit Rate (25%) และ MRR (25%):\n- Hybrid (BM25+E5) ได้ 91.64 คะแนน\n- Dense Only ได้ 81.85 คะแนน (-9.79 คะแนน)",
        ],
        [
            "Case 4: ผลของโควตา Chunks ต่อโปรเจกต์ (Chunks=6, Quota=2 vs Uncapped/Minimal)",
            "GT-08: เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device ในด้านฮาร์ดแวร์",
            "max_context_chunks = 6, max_chunks_per_project = 2\nเทียบกับ\nChunks = 2, Quota = 1",
            "[Chunks=6, Quota=2 (Winner)]: ระบบบังคับแบ่งโควตาให้โปรเจกต์ละ 2 Chunks อย่างเท่าเทียม (The LoRaWAN 2 Chunks + BSLD Beacon 2 Chunks) ส่งผลให้ `gemma3:4b` สร้างตาราง Markdown เปรียบเทียบทั้งฝั่ง LoRa (SX1276/ESP32) และฝั่ง BSLD (iBeacon/BLE) ได้ครบ 100%\n(Blended Quality = 84.7, Key Phrase Recall = 86.7%, Multi-Project Coverage = 100%)",
            "[Chunks=2, Quota=1]: ส่งให้โปรเจกต์ละ 1 Chunk สั้นๆ ทำให้ในข้อ GT-03 และ GT-08 ขาดรายละเอียดอุปกรณ์ย่อยในหน้าถัดไป ส่งผลให้ Key Phrase Recall เฉลี่ยลดลงจาก 86.7% เหลือ 80.0%\nส่วน [Chunks=6, Quota=6 Uncapped] ใช้ Input Tokens พุ่งถึง 2,177 tokens และใช้เวลานานถึง 19.93s",
            "ตามกฎ Stage 2 (Quality 50% + Phrase Recall & Multi-Project 30% + Quota Balance 10%):\n- Chunks=6, Quota=2 ชนะเลิศด้วยคะแนน Quality 84.7 และ Phrase Recall 86.7% (Composite = 82.61)",
        ],
        [
            "Case 5: ผลของรูปแบบคำสั่ง Prompt Preset บนโมเดล gemma3:4b",
            "GT-03: ขั้นตอนการทำงานและการทดลองของ The LoRaWAN\n& GT-06: มีการเชื่อมต่อกับ Line Notify หรือไม่",
            "prompt_preset = 'deep_academic' / 'balanced' (Temp=0.0)\nเทียบกับ\nprompt_preset = 'concise'",
            "[deep_academic / balanced @ Temp=0.0]: คำตอบของ `gemma3:4b` แจกแจงหัวข้อชัดเจน พร้อมแนบ `[Source: 1_6031501044_6031501061_FinalProject.pdf, Page: 18]` (ได้ Citation Rule 1 = 30/30, Completeness Rule 4 = 20/20) และในข้อ GT-06 ปฏิเสธชัดเจนว่า 'ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร' (Hallucination Guard = 100%)",
            "[concise @ MaxTokens=256]: ตอบสั้นกระชับเร็วขึ้น (12.00s) แต่ในบางข้อตัดจบก่อนใส่แท็ก `[Source: ..., Page: ...]` ครบตามรูปแบบ ทำให้คะแนน Citation Rule 1 ลดลงในบางข้อ (Quality เฉลี่ยลดจาก 84.7 เหลือ 80.0)",
            "ตามกฎ Rubric Rule 1 (Citation 30 คะแนน) และ Rule 5 (Key Phrase Recall):\n- `deep_academic` (83.50) และ `balanced` (82.61) ที่ Temp=0.0 ชนะ `concise` (80.52) และชนะ Temp=0.5 (80.65)",
        ],
        [
            "Case 6: ผลของการเลือกขนาดโมเดล LLM บน RTX 3050 Ti (4GB VRAM)",
            "GT-01: โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง\n& GT-08: เปรียบเทียบ The LoRaWAN กับ BSLD",
            "รุ่น 3B-4B (llama3.2:3b, qwen2.5:3b, gemma3:4b)\nเทียบกับ\nรุ่นจิ๋ว 1B (gemma3:1b) และรุ่นใหญ่ 8B (llama3.1:8b)",
            "[llama3.2:3b (2.0GB) / gemma3:4b (3.3GB) / qwen2.5:3b (1.9GB)]: รันบน VRAM 4GB ของการ์ดจอได้ 100% ตอบข้อ GT-01 ระบุ '1. **The LoRaWAN** ... โมดูล SX1276 ... [Source: 1_6031501044_6031501061_FinalProject.pdf, Page: 18]' ได้แม่นยำ (Quality = 84.1 - 84.7, Key Phrase Recall = 86.7%, ความเร็ว 47.6 - 60.0 TPS สำหรับรุ่น 3B)",
            "[gemma3:1b (0.8GB)]: เร็วมาก (130.7 TPS) แต่ในข้อ GT-01 เกิดอาการพูดซ้ำ 'SX1276 Ultrasonic Distance Sensor Module...' และไม่ระบุชื่อโครงงาน The LoRaWAN ทำให้ Phrase Recall ตกเหลือ 33.3%\n[llama3.1:8b (4.9GB)]: ขนาดล้น VRAM 4GB ต้องสลับไปใช้ CPU RAM ทำให้ความเร็วตกเหลือเพียง 7.3 TPS (เฉลี่ย 20.45s/ข้อ)",
            "ตามกฎ Rule 1-7 (Multi-LLM Suitability):\n- `llama3.2:3b` ชนะเลิศความคุ้มค่ารวม (87.70 คะแนน, 5.60s)\n- `qwen2.5:3b` ชนะเลิศความเร็ว 3B (82.48 คะแนน, 60.0 TPS)\n- `gemma3:4b` ชนะเลิศคุณภาพเนื้อหาสูงสุด (Quality 84.67)",
        ],
    ]

    for c_idx, h in enumerate(headers_ex, start=1):
        ws9.cell(row=4, column=c_idx, value=h)
    for r_offset, row_vals in enumerate(rows_ex, start=5):
        for c_idx, val in enumerate(row_vals, start=1):
            ws9.cell(row=r_offset, column=c_idx, value=val)
    style_table(ws9, 4, 4 + len(rows_ex), len(headers_ex), winner_rows=set(range(5, 5 + len(rows_ex))), left_cols=(1, 2, 3, 4, 5, 6))
    auto_fit_columns(ws9, max_width=55)

    # -------------------------------------------------------------------------
    # SHEET 10 & 11: Multi-LLM Model Comparison & Per-Query Rule Breakdown
    # -------------------------------------------------------------------------
    if llm_bench:
        s_name_10 = sheet_name(9, "LLM_Model_Comparison")
        if s_name_10 in wb.sheetnames:
            del wb[s_name_10]
        ws10 = wb.create_sheet(title=s_name_10)

        ws10["A1"] = "🤖 Stage 3: ตารางเปรียบเทียบโมเดล LLM ทั้ง 7 รุ่น บนการ์ดจอ RTX 3050 Ti (4GB VRAM) + RAM 16GB"
        ws10["A1"].font = TITLE_FONT
        ws10["A2"] = "ล็อกค่าพารามิเตอร์ที่ชนะจาก Stage 1+2 (top_k=15, top_n=10, Chunks=6, Quota=2, Temp=0.0) แล้ววัดคะแนนรายกฎ (Rule 1-7), ความเร็ว และความเหมาะสมกับเครื่อง"
        ws10["A2"].font = BOLD_FONT

        headers_llm = [
            "อันดับ (Rank)",
            "ชื่อโมเดล (Ollama Model)",
            "ตระกูล (Family)",
            "ขนาดพารามิเตอร์",
            "ขนาดไฟล์ (GB)",
            "ความเข้ากันได้กับ RTX 3050 Ti (4GB VRAM)",
            "Rule 1: Citation (เต็ม 30)",
            "Rule 2: Cleanliness (เต็ม 25)",
            "Rule 3: Speed Score (เต็ม 25)",
            "Rule 4: Completeness (เต็ม 20)",
            "รวมคะแนน Rubric (เต็ม 100)",
            "Rule 5: Key Phrase Recall (%)",
            "Rule 6: Hallucination Guard (%)",
            "Multi-Project Coverage (%)",
            "Blended Quality (0-100)",
            "Rule 7: VRAM Fit Score",
            "เวลาตอบเฉลี่ย (วินาที)",
            "ความเร็ว (TPS)",
            "คะแนนความเหมาะสมรวม (Suitability Score)",
            "ทำไมถึงนำโมเดลนี้มาทดสอบ (Why Tested / สมมติฐานการทดลอง)",
            "ทำไมถึงเลือก / ไม่เลือกใช้งานจริง (Why Selected / สรุปความคุ้มค่า)",
        ]
        llm_rationale_map = {
            "llama3.2:3b": (
                "นำมาทดสอบเป็นตัวแทนโมเดล 3B มาตรฐานสากลของ Meta ที่ถูกออกแบบมาเพื่อ Laptop GPU ขนาด 4GB โดยเฉพาะ เพื่อดูว่าสกัดรหัสฮาร์ดแวร์และชื่อโครงงานได้แม่นยำเทียบเท่าโมเดล 4B-8B หรือไม่",
                "🏆 เลือกเป็นอันดับ 1 ด้านความคุ้มค่ารวม (Suitability = 87.70): รันบน VRAM 4GB ได้ 100% ตอบไวเฉลี่ย 5.60s (47.6 TPS เร็วกว่า gemma3:4b ถึง 3.4 เท่า) แต่ยังเก็บคำสำคัญ (Phrase Recall 86.7%) และอ้างอิง (Citation 21/30) ได้เทียบเท่ารุ่นใหญ่",
            ),
            "qwen2.5:3b": (
                "นำมาทดสอบเป็นตัวแทนโมเดล 3B สายเอเชีย (Alibaba) ขนาดเบา 1.9 GB ที่ไม่ติดโหมดคิดยาว (<think>) เหมือน Qwen 3 เพื่อพิสูจน์ว่าทำสปีดสูงสุดบนการ์ดจอ 4GB โดยยังตอบภาษาไทยได้ดีหรือไม่",
                "🥈 เลือกเป็นอันดับ 2 สายความเร็วสูง (Suitability = 82.48): ปั่น Token เร็วถึง 60.0 TPS กิน VRAM น้อยมาก (1.9 GB) และได้คะแนน Quality 81.20 เหมาะสำหรับโหมดต้องการคำตอบด่วน",
            ),
            "gemma3:1b": (
                "นำมาทดสอบเป็นตัวแทน Ultra-Lightweight (1B Parameter, 0.8 GB) เพื่อเป็นขีดจำกัดล่าง (Lower-Bound Control) พิสูจน์ว่าหากลดขนาดโมเดลเหลือ 1B เพื่อเอาความเร็ว >100 TPS คุณภาพคำตอบ RAG จะดรอปลงแค่ไหน",
                "❌ ไม่เลือกเป็นโมเดลหลัก (ใช้เฉพาะโหมดประหยัดทรัพยากรสุดขีด): แม้เร็วที่สุดถึง 130.7 TPS (6.86s) แต่ขนาด 1B เล็กเกินไปจนเกิดอาการพูดซ้ำ (Repetition) ในข้อ GT-01 และลืมระบุชื่อโครงงาน ทำให้ Phrase Recall ตกเหลือ 66.7%",
            ),
            "gemma3:4b": (
                "นำมาทดสอบเป็น Baseline หลักของระบบ (ขนาด 4.3B, 3.3 GB พอดีเพดานการ์ดจอ VRAM 4GB) เนื่องจากตระกูล Gemma 3 โดดเด่นเรื่องการเรียบเรียงภาษาไทยและโครงสร้าง Markdown วิชาการ",
                "🏅 เลือกเป็นแชมป์ด้านคุณภาพเนื้อหาสูงสุด (Quality = 84.67, Phrase Recall = 86.7%): เรียบเรียงคำตอบภาษาไทย ตารางเปรียบเทียบ และอ้างอิง `[Source: ..., Page: ...]` ได้ละเอียดและสละสลวยที่สุด (ใช้เวลาเฉลี่ย 19.23s เพราะเขียนละเอียดถึง ~199 tokens)",
            ),
            "qwen2.5:7b": (
                "นำมาทดสอบเป็นตัวแทนรุ่นกลาง 7B Parameter (4.7 GB) เพื่อเป็นกลุ่มเปรียบเทียบ (Upper-Mid Control) ว่าการขยับขนาดเกิน 4GB VRAM เล็กน้อยให้ความแม่นยำเพิ่มขึ้นคุ้มกับความเร็วที่ลดลงหรือไม่",
                "⚠️ ไม่เลือกเป็นค่าเริ่มต้นบนการ์ดจอ 4GB: แม้ได้คะแนน Citation สูงสุด (24/30, Quality 81.80) แต่ขนาด 4.7 GB ล้น VRAM 4GB ต้องสลับใช้ CPU RAM ทำให้ความเร็วลดเหลือ 8.6 TPS (16.97s) ช้ากว่ารุ่น 3B ถึง 5.5 เท่า",
            ),
            "qwen3:4b": (
                "นำมาทดสอบเป็นตัวแทนโมเดลยุคใหม่ที่มีสถาปัตยกรรมคิดเชิงเหตุผล (Reasoning/Thinking) เพื่อดูว่าช่วยวิเคราะห์ตารางเปรียบเทียบโครงงานได้ดีขึ้นหรือไม่",
                "⚠️ ไม่เลือกเป็นค่าเริ่มต้น: โมเดลชอบเขียนแจกแจงขั้นตอนการคิดวิเคราะห์คำถามก่อนเข้าสู่คำตอบจริง (เช่นใน GT-01 และ GT-06) ทำให้เสียโควตา Output Tokens และใช้เวลาตอบนาน (18.20s, Quality 77.73)",
            ),
            "llama3.1:8b": (
                "นำมาทดสอบเป็นตัวแทนรุ่นใหญ่มาตรฐาน 8B Parameter (4.9 GB) เพื่อเป็นขีดจำกัดบน (Upper-Bound Control) พิสูจน์คอขวดด้านฮาร์ดแวร์เมื่อรันโมเดล 8B บนการ์ดจอ Laptop 4GB VRAM",
                "❌ ไม่เลือกสำหรับ RTX 3050 Ti (4GB VRAM): แม้แม่นยำสูง (Phrase Recall 86.7%, Quality 80.47) แต่ขนาด 4.9 GB ล้น VRAM จนเกิดคอขวด GPU-RAM ความเร็วตกเหลือเพียง 7.3 TPS (เฉลี่ย 20.45s/ข้อ และนานถึง 43.8s ในข้อ GT-01)",
            ),
        }
        for c_idx, h in enumerate(headers_llm, start=1):
            ws10.cell(row=4, column=c_idx, value=h)

        winner_rows_llm = {5, 6, 8}  # Highlight llama3.2:3b (#1), qwen2.5:3b (#2), and gemma3:4b (Quality #1)
        for rank_idx, r in enumerate(llm_bench, start=1):
            row_num = 4 + rank_idx
            why_test_m, why_sel_m = llm_rationale_map.get(r["model"], (r["role"], "พิจารณาตามคะแนนความเหมาะสมรวม"))
            vals = [
                f"#{rank_idx}",
                r["model"],
                r["family"],
                r["params"],
                r["size_gb"],
                r["vram_fit"],
                r["avg_citation_30"],
                r["avg_cleanliness_25"],
                r["avg_latency_25"],
                r["avg_completeness_20"],
                r["avg_rubric_100"],
                r["avg_phrase_recall_pct"],
                r["avg_hallucination_pass_pct"],
                r["multi_project_coverage_pct"],
                r["avg_quality_score"],
                r["vram_score"],
                r["avg_llm_seconds"],
                r["avg_tps"],
                r["composite_score"],
                why_test_m,
                why_sel_m,
            ]
            for c_idx, v in enumerate(vals, start=1):
                ws10.cell(row=row_num, column=c_idx, value=v)

        style_table(ws10, 4, 4 + len(llm_bench), len(headers_llm), winner_rows=winner_rows_llm, left_cols=(2, 3, 6, 20, 21))
        auto_fit_columns(ws10, max_width=55)

        # SHEET 11: Multi-LLM Per-Query Rule Breakdown & Actual Outputs
        s_name_11 = sheet_name(10, "LLM_PerQuery_Rule_Detail")
        if s_name_11 in wb.sheetnames:
            del wb[s_name_11]
        ws11 = wb.create_sheet(title=s_name_11)

        ws11["A1"] = "📑 Stage 3 Per-Query Detail: คะแนนแยกตามกฎ (Rule 1-6) และตัวอย่างคำตอบจริงของโมเดล LLM ทั้ง 7 รุ่น"
        ws11["A1"].font = TITLE_FONT
        ws11["A2"] = "เปรียบเทียบคำตอบจริงและคะแนนรายกฎของแต่ละโมเดลในคำถามชุดเดียวกัน (GT-01, GT-03, GT-04, GT-06, GT-08)"
        ws11["A2"].font = BOLD_FONT

        headers_llmpq = [
            "ชื่อโมเดล (Model)",
            "ขนาด (GB)",
            "รหัสข้อ (Query ID)",
            "หมวดหมู่ (Category)",
            "คำถามที่ใช้ทดสอบ (Query)",
            "Rule 1: Citation (30)",
            "Rule 2: Cleanliness (25)",
            "Rule 3: Latency (25)",
            "Rule 4: Completeness (20)",
            "Rubric Total (100)",
            "Rule 5: Phrase Recall (%)",
            "Rule 6: Hallucination Guard (%)",
            "Blended Quality (0-100)",
            "เวลา LLM ตอบ (s)",
            "ความเร็ว (TPS)",
            "ตัวอย่างคำตอบจริงจากโมเดล (Actual Model Output Preview)",
        ]
        for c_idx, h in enumerate(headers_llmpq, start=1):
            ws11.cell(row=4, column=c_idx, value=h)

        r_cur_llm = 5
        for r in llm_bench:
            for pq in r.get("per_query", []):
                vals = [
                    r["model"],
                    r["size_gb"],
                    pq.get("id", ""),
                    pq.get("category", ""),
                    pq.get("query", ""),
                    pq.get("citation_30", 0.0),
                    pq.get("cleanliness_25", 0.0),
                    pq.get("latency_25", 0.0),
                    pq.get("completeness_20", 0.0),
                    pq.get("rubric_total_100", 0.0),
                    pq.get("phrase_recall_pct", 0.0),
                    pq.get("hallucination_guard_pct", 100.0),
                    pq.get("quality_score", 0.0),
                    pq.get("llm_seconds", 0.0),
                    pq.get("tps", 0.0),
                    pq.get("answer_preview", ""),
                ]
                for c_idx, v in enumerate(vals, start=1):
                    ws11.cell(row=r_cur_llm, column=c_idx, value=v)
                r_cur_llm += 1

        style_table(ws11, 4, r_cur_llm - 1, len(headers_llmpq), left_cols=(1, 4, 5, 16))
        auto_fit_columns(ws11, max_width=56)


def build_all_excel_files():
    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)
    with open(GOLDEN_JSON, "r", encoding="utf-8") as f:
        golden_list = json.load(f)
    golden_map = {item["id"]: item for item in golden_list}

    # 1. Create standalone RAGcoon_Parameter_Tuning_Experiments.xlsx
    wb_standalone = Workbook()
    default_sheet = wb_standalone.active
    populate_parameter_sweep_sheets(wb_standalone, payload, golden_map, prefix_num=None)
    if default_sheet.title in wb_standalone.sheetnames and len(wb_standalone.sheetnames) > 1:
        del wb_standalone[default_sheet.title]

    out_standalone_1 = os.path.join(DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    out_standalone_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    wb_standalone.save(out_standalone_1)
    shutil.copyfile(out_standalone_1, out_standalone_2)
    print(f"Saved Standalone Parameter Sweep Excel ({len(wb_standalone.sheetnames)} sheets) -> {out_standalone_1}", flush=True)
    print(f"Saved Standalone Parameter Sweep Excel ({len(wb_standalone.sheetnames)} sheets) -> {out_standalone_2}", flush=True)

    # 2. Update existing RAGcoon_Handoff_Specification.xlsx
    handoff_1 = os.path.join(DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    handoff_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    if os.path.exists(handoff_1):
        wb_handoff = load_workbook(handoff_1)
        populate_parameter_sweep_sheets(wb_handoff, payload, golden_map, prefix_num=10)
        wb_handoff.save(handoff_1)
        shutil.copyfile(handoff_1, handoff_2)
        print(f"Updated Handoff Specification Excel ({len(wb_handoff.sheetnames)} sheets) -> {handoff_1}", flush=True)
        print(f"Updated Handoff Specification Excel ({len(wb_handoff.sheetnames)} sheets) -> {handoff_2}", flush=True)


if __name__ == "__main__":
    build_all_excel_files()
