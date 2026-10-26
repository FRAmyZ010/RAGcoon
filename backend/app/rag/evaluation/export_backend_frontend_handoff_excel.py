"""
Module: export_backend_frontend_handoff_excel.py
Description:
    Generates the comprehensive Backend & Frontend Update Handoff Excel workbook:
      - data/RAGcoon_Backend_Frontend_Update_Handoff.xlsx
      - backend/data/RAGcoon_Backend_Frontend_Update_Handoff.xlsx
    And also appends the Backend/Frontend Action Plan sheet to:
      - data/RAGcoon_Handoff_Specification.xlsx
      - backend/data/RAGcoon_Handoff_Specification.xlsx
      - data/RAGcoon_Parameter_Tuning_Experiments.xlsx
      - backend/data/RAGcoon_Parameter_Tuning_Experiments.xlsx
"""

import os
import shutil
import sys
from datetime import datetime
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
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BACKEND_DATA_DIR = os.path.join(BACKEND_DIR, "data")

# Styling Constants
HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
P0_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
P1_FILL = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")
ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

HEADER_FONT = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Tahoma", size=14, bold=True, color="1E3A8A")
SUBTITLE_FONT = Font(name="Tahoma", size=10, bold=True, color="334155")
BOLD_FONT = Font(name="Tahoma", size=10, bold=True, color="0F172A")
P0_FONT = Font(name="Tahoma", size=10, bold=True, color="065F46")
REGULAR_FONT = Font(name="Tahoma", size=10, bold=False, color="1E293B")
CODE_FONT = Font(name="Consolas", size=9.5, bold=False, color="0F172A")

THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def style_sheet_table(
    ws,
    start_row: int,
    end_row: int,
    num_cols: int,
    highlight_rows: set[int] | None = None,
    warn_rows: set[int] | None = None,
    left_cols: tuple[int, ...] = (2, 3, 4, 5, 6),
    code_cols: tuple[int, ...] = (),
):
    highlight_rows = highlight_rows or set()
    warn_rows = warn_rows or set()

    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[start_row].height = 30

    for r_idx in range(start_row + 1, end_row + 1):
        is_hi = r_idx in highlight_rows
        is_warn = r_idx in warn_rows
        row_fill = P0_FILL if is_hi else (P1_FILL if is_warn else (ZEBRA_FILL if r_idx % 2 == 0 else WHITE_FILL))
        max_lines = 1
        for c_idx in range(1, num_cols + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.fill = row_fill
            if c_idx in code_cols:
                cell.font = CODE_FONT
            elif is_hi:
                cell.font = P0_FONT
            else:
                cell.font = REGULAR_FONT
            val_str = str(cell.value or "")
            lines = val_str.count("\n") + 1
            if len(val_str) > 65:
                lines = max(lines, (len(val_str) // 60) + 1)
            if lines > max_lines:
                max_lines = lines
            align_h = "left" if (c_idx in left_cols or c_idx in code_cols) else "center"
            cell.alignment = Alignment(horizontal=align_h, vertical="top", wrap_text=True)
            cell.border = THIN_BORDER
        ws.row_dimensions[r_idx].height = max(24, min(max_lines * 16 + 8, 170))


def auto_fit_sheet(ws, max_width: int = 56):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            for line in val_str.split("\n"):
                if len(line) > max_len:
                    max_len = len(line)
        ws.column_dimensions[col_letter].width = max(13, min(max_len + 4, max_width))


def build_action_plan_rows():
    return [
        [
            "ACT-01",
            "P0 (ด่วนที่สุด)",
            "Backend (FastAPI)",
            "อัปเดต ChatRequest & rag_services.py ให้ส่งต่อ llm_model, llm_provider และ config",
            "backend/app/schemas/chat.py\nbackend/app/services/rag_services.py\nbackend/app/api/v1/chat.py",
            "ปัจจุบัน answer_question() และ stream_answer_question() ในฝั่ง RAG รองรับการเปลี่ยนโมเดล (7 รุ่น) และโปรไฟล์พารามิเตอร์แล้ว แต่ rag_services.py บรรทัด 136 และ 220 ยังเรียกแบบไม่ส่งพารามิเตอร์ ทำให้ผู้ใช้เลือกโมเดลหรือโปรไฟล์รายคำถามไม่ได้",
            "เพิ่มฟิลด์ llm_provider, llm_model, profile_name ใน ChatRequest และส่งเข้าไปใน answer_question() / stream_answer_question()",
        ],
        [
            "ACT-02",
            "P0 (ด่วนที่สุด)",
            "Backend & DevOps",
            "อัปเดตค่า Default พารามิเตอร์และโมเดลตามผลการทดลองที่ชนะเลิศ (Optimal Tuned Lock)",
            "backend/app/rag/retrieval/rag_config.py\nbackend/.env\ndocker-compose.yml",
            "ผลการทดลองพิสูจน์แล้วว่า top_k=15, rerank_top_n=10, max_context_chunks=6, max_chunks_per_project=2, temp=0.0 ให้ Hit Rate 100%, MRR 0.9231 และ Quality 84.67 โดยเร็วขึ้นกว่าเดิมมาก ส่วนโมเดลบน RTX 3050 Ti แนะนำ llama3.2:3b (ไว 5.6s) และ gemma3:4b (ภาษาไทยละเอียดสุด)",
            "ตั้งค่าเริ่มต้นใน .env หรือให้ระบบใช้ Active Profile จาก rag_config.py (ตั้งค่าเริ่มต้นแล้ว) และรัน docker-compose up เพื่อให้ Container ollama ดึงโมเดลทั้ง 6-7 รุ่นอัตโนมัติ",
        ],
        [
            "ACT-03",
            "P0 (ด่วนที่สุด)",
            "Frontend (UI)",
            "สร้าง Dropdown สลับโมเดล LLM ทั้ง 7 รุ่น บนหน้า Chat พร้อมป้ายแนะนำความเร็ว/VRAM",
            "frontend/src/components/Chat/... (Chat Header / Model Selector)",
            "ฝั่ง RAG ได้ติดตั้งและทดสอบโมเดล 7 รุ่นใน AVAILABLE_LLM_PROFILES เรียบร้อยแล้ว ผู้ใช้ควรเลือกสลับโหมดได้ตามงาน เช่น โหมดตอบไว (llama3.2:3b / qwen2.5:3b) หรือโหมดวิชาการละเอียด (gemma3:4b)",
            "เรียก GET /api/v1/chat/llm-profiles เพื่อแสดงรายการโมเดล และเรียก POST /api/v1/chat/set-active-llm หรือส่ง llm_model ไปกับ POST /api/v1/chat/query-stream",
        ],
        [
            "ACT-04",
            "P1 (สำคัญมาก)",
            "Backend (FastAPI)",
            "เปิดใช้งาน API Endpoints สำหรับปรับจูนพารามิเตอร์อิสระและเซฟโปรไฟล์ใหม่ (RAG Config API)",
            "backend/app/api/v1/ai_config.py (สร้างใหม่)\nbackend/app/api/v1/router.py",
            "ฝั่ง RAG สร้างฟังก์ชัน list_all_configs(), save_custom_config(), set_active_rag_config_by_name(), delete_custom_config() และ compare_two_configs() ไว้เสร็จสมบูรณ์แล้ว แต่ยังไม่มี Route ใน api/v1/router.py ให้ Frontend เรียกใช้",
            "สร้าง Router `/api/v1/rag-config` ผูกเข้ากับฟังก์ชันใน `app.rag.retrieval.rag_config` และ `app.rag.evaluation.config_benchmark` (มีโค้ดตัวอย่างให้ใน Sheet 03 และ Sheet 04)",
        ],
        [
            "ACT-05",
            "P1 (สำคัญมาก)",
            "Frontend (UI)",
            "สร้างหน้าจอ Admin RAG Parameter Studio (Sliders + Toggles เปิด/ปิดโมดูล + ปุ่ม Save as New Profile)",
            "frontend/src/pages/admin/... (AI Config / Parameter Studio)",
            "เพื่อให้ผู้ดูแลระบบปรับค่า top_k [5..100], rerank_top_n [1..30], max_context_chunks [2..15], max_chunks_per_project [1..5], เปิด/ปิด Hybrid BM25, Reranker, Boilerplate Filter, Fast-Path และเซฟเป็นโปรไฟล์ทดสอบชื่อใหม่ผ่านหน้าเว็บได้ทันที",
            "สร้าง UI Sliders + Switch Toggles เชื่อมกับ POST /api/v1/rag-config/profiles และปุ่มเปรียบเทียบโปรไฟล์เก่า vs ใหม่ (POST /api/v1/rag-config/compare)",
        ],
        [
            "ACT-06",
            "P1 (สำคัญมาก)",
            "Backend & Frontend",
            "ส่งข้อมูล Performance Metrics (ความเร็ว TPS, Input/Output Tokens, Token Breakdown) ไปแสดงใต้คำตอบ",
            "backend/app/schemas/chat.py\nbackend/app/services/rag_services.py\nfrontend/src/components/Chat/MessageItem",
            "ฝั่ง RAG คำนวณ gen_speed_tps, input_tokens, output_tokens และ token_breakdown ส่งออกมาใน dict `performance` แล้ว แต่ rag_services.py ตัดทิ้งก่อนส่งให้ Frontend",
            "เพิ่มฟิลด์ `performance` และ `model` ใน ChatResponse และใน SSE `metadata` event เพื่อให้ Frontend แสดงป้ายกำกับ เช่น `⚡ 47.6 TPS | ⏱️ 5.6s | 🪙 1,519 in / 93 out tokens | 🤖 llama3.2:3b`",
        ],
        [
            "ACT-07",
            "P1 (สำคัญมาก)",
            "Frontend (UI)",
            "อัปเกรดการ์ดเอกสารอ้างอิง (Citation Card) ให้แสดงเลขหน้ารวม (pages_formatted) และข้อมูลโครงงานครบถ้วน",
            "frontend/src/components/Chat/CitationCard",
            "ฝั่ง RAG ได้ยุบรวม Chunks จากไฟล์เดียวกันและสร้างฟิลด์ `pages_formatted` (เช่น '17, 18, 22'), `author`, `advisor`, `year`, `program` ส่งมาใน `citations` เรียบร้อยแล้ว",
            "แสดงเลขหน้าทั้งหมดจาก `citation.pages_formatted` แสดงชื่อผู้จัดทำ/อาจารย์ที่ปรึกษา และทำลิงก์คลิกเปิด PDF ไปยังเลขหน้าเริ่มต้น (`/api/v1/documents/{document_id}/file#page={page}`)",
        ],
        [
            "ACT-08",
            "P2 (ต่อยอด)",
            "Backend & Frontend",
            "เพิ่มหน้า Dashboard แสดงผลการทดลองจูนพารามิเตอร์และตารางจัดอันดับ LLM 7 รุ่น",
            "backend/app/api/v1/dashboard.py\nfrontend/src/pages/admin/dashboard",
            "มีไฟล์ผลลัพธ์มาตรฐาน `data/parameter_sweep_results.json` และ `best_rag_config.json` ที่เก็บผลลัพธ์ครบทั้ง Stage 1, Stage 2 และ Stage 3 (7 โมเดล LLM) พร้อมกฎการให้คะแนน Rule 1-7",
            "เพิ่ม Endpoint `GET /api/v1/dashboard/rag-benchmark` อ่านไฟล์ `parameter_sweep_results.json` ส่งให้ Frontend วาดกราฟเปรียบเทียบความแม่นยำและความเร็วของแต่ละพารามิเตอร์/โมเดล",
        ],
    ]


def populate_handoff_workbook(wb: Workbook):
    # -------------------------------------------------------------------------
    # SHEET 1: Executive Action Plan (Backend, Frontend, DevOps)
    # -------------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "01_Executive_Action_Plan"
    ws1["A1"] = "🚀 แผนส่งมอบงานและรายการอัปเดตสำหรับทีม Backend & Frontend (Post-Parameter Tuning & 7-LLM Benchmark Handoff)"
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = f"อัปเดตล่าสุด: {datetime.now().strftime('%Y-%m-%d %H:%M')} | สถานะฝั่ง RAG Engine: สร้างและทดสอบเสร็จสมบูรณ์ 100% (พร้อมเชื่อมต่อ API & UI)"
    ws1["A2"].font = SUBTITLE_FONT

    headers_1 = [
        "รหัสงาน (Task ID)",
        "ความสำคัญ (Priority)",
        "ทีมรับผิดชอบ (Owner)",
        "หัวข้อสิ่งที่ต้องทำเพิ่ม (Action Item)",
        "ไฟล์ที่ต้องแก้ไข / สร้างเพิ่ม (Target Files)",
        "สาเหตุและสิ่งที่ฝั่ง RAG เตรียมไว้ให้แล้ว (Why Needed & What RAG Already Built)",
        "รายละเอียดการอัปเดตที่ต้องทำ (Exact Implementation Steps)",
    ]
    rows_1 = build_action_plan_rows()
    for c_idx, h in enumerate(headers_1, start=1):
        ws1.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_1, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws1.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws1,
        4,
        4 + len(rows_1),
        len(headers_1),
        highlight_rows={5, 6, 7},
        warn_rows={8, 9, 10, 11},
        left_cols=(4, 5, 6, 7),
        code_cols=(5,),
    )
    auto_fit_sheet(ws1, max_width=54)

    # -------------------------------------------------------------------------
    # SHEET 2: Optimal Config & LLM Defaults to Apply
    # -------------------------------------------------------------------------
    ws2 = wb.create_sheet(title="02_Optimal_Config_To_Apply")
    ws2["A1"] = "🏆 สรุปค่าพารามิเตอร์และโมเดล LLM ที่ชนะการทดลอง สำหรับนำไปตั้งเป็นค่า Default ของระบบ"
    ws2["A1"].font = TITLE_FONT
    ws2["A2"] = "เปรียบเทียบค่าเดิม (Before Tuning) กับค่าใหม่ที่ดีที่สุด (After Tuning) พร้อมเหตุผลที่นำมาทดสอบและเหตุผลที่เลือก"
    ws2["A2"].font = SUBTITLE_FONT

    headers_2 = [
        "ลำดับ",
        "ชื่อพารามิเตอร์ / โมเดล",
        "ค่าเดิมก่อนจูน (Old Default)",
        "ค่าใหม่ที่แนะนำ (New Optimal Default)",
        "ตัวแปรใน .env / RAGConfig",
        "ทำไมถึงนำมาทดสอบ (Why Tested)",
        "ทำไมถึงเลือกค่าใหม่นี้ (Why Selected & Impact)",
    ]
    rows_2 = [
        [
            1,
            "ขนาดการดึงข้อมูลเบื้องต้น (top_k)",
            "30",
            "15",
            "RAG_TOP_K=15\n(config.top_k)",
            "เพื่อหาขนาด Candidate Pool จาก Qdrant ที่ไม่แคบจนเนื้อหาตกหล่น และไม่กว้างจนค้นหาช้า",
            "ชนะเลิศ Exp 1 (Composite = 88.15, MRR = 0.8718): แม่นยำเท่ากับ 30 แต่ลดเวลาค้นหาลงจาก 675ms เหลือ 468ms (และเร็วกว่า top_k=100 ถึง 3.7 เท่า)",
        ],
        [
            2,
            "จุดตัดหลังจัดอันดับใหม่ (rerank_top_n)",
            "5",
            "10 (คู่กับ Context Cap = 6)",
            "RAG_RERANK_TOP_N=10\n(config.rerank_top_n)",
            "เพื่อหาจำนวน Chunks ที่ผ่าน Cross-Encoder Reranker ก่อนส่งให้ตัวจัดโควตาโปรเจกต์",
            "ชนะเลิศ Exp 2 (Composite = 90.05, Hit Rate = 100.0%, Recall@N = 96.2%): ป้องกันเอกสารของโปรเจกต์ที่ 2 หลุดขอบในคำถามเปรียบเทียบ",
        ],
        [
            3,
            "จำนวน Chunks สูงสุดเข้า LLM (max_context_chunks)",
            "5",
            "6",
            "RAG_MAX_CONTEXT_CHUNKS=6\n(config.max_context_chunks)",
            "เพื่อหาขนาดบริบทที่พอดีกับการ์ดจอ RTX 3050 Ti (4GB VRAM) โดยไม่เกิดอาการสำลักบริบท (Lost-in-the-Middle)",
            "ชนะเลิศ Exp 4 (Quality = 84.67, Key Phrase Recall = 86.7%): ให้ข้อมูลครบถ้วนกว่า 2-5 Chunks และไม่เปลือง Input Tokens เหมือน 10-15 Chunks",
        ],
        [
            4,
            "โควตา Chunks ต่อโปรเจกต์ (max_chunks_per_project)",
            "2",
            "2",
            "config.max_chunks_per_project = 2",
            "เพื่อป้องกันปัญหาโปรเจกต์เดียวกินพื้นที่ Chunks ทั้งหมดในคำถามเปรียบเทียบหลายโครงงาน (GT-08)",
            "เมื่อใช้คู่กับ max_context_chunks = 6 จะแบ่งให้โปรเจกต์ละ 2 Chunks ได้ถึง 3 โปรเจกต์อย่างยุติธรรม (Multi-Project Coverage = 100.0%)",
        ],
        [
            5,
            "สวิตช์โมดูลฝั่งค้นหาทั้ง 4 ตัว (Ablation Switches)",
            "เปิดใช้งาน",
            "เปิดครบทั้ง 4 ตัว (True ทั้งหมด)",
            "enable_hybrid=True\nenable_reranker=True\nenable_boilerplate_filter=True\nenable_fast_path=True",
            "ทดสอบปิดทีละตัวเพื่อพิสูจน์ว่าแต่ละโมดูลจำเป็นจริงหรือไม่ (Ablation Study)",
            "Full Pipeline ชนะขาดลอย (Composite = 91.64, Hit = 100%, MRR = 0.9231, ขยะ = 0.0%, เวลา 312.4ms) เทียบกับระบบเก่าที่ได้เพียง 65.87",
        ],
        [
            6,
            "รูปแบบคำสั่งและอุณหภูมิ (prompt_preset & temperature)",
            "balanced / 0.0",
            "deep_academic หรือ balanced ที่ temperature = 0.0",
            "config.prompt_preset\nconfig.temperature = 0.0",
            "ทดสอบรูปแบบคำสั่ง 4 แบบ และ Temperature [0.0, 0.2, 0.5] เพื่อดูความแม่นยำในการอ้างอิงและการป้องกันการมั่ว",
            "Temp = 0.0 ให้คำตอบเที่ยงตรง 100% ผ่านกฎ Anti-Hallucination Guard เต็ม 100% และเร็วกว่า Temp 0.2/0.5",
        ],
        [
            7,
            "โมเดล LLM แนะนำสำหรับโหมดเร็ว+แม่นยำ (Fast & Accurate Default)",
            "gemma3:4b (19.23s)",
            "llama3.2:3b (2.0 GB) หรือ qwen2.5:3b (1.9 GB)",
            "OLLAMA_MODEL=llama3.2:3b\n(หรือสลับผ่าน UI)",
            "ทดสอบโมเดลขนาด 3B (2.0 GB) บน RTX 3050 Ti เพื่อแก้ปัญหาเวลาตอบนานของโมเดลรุ่นใหญ่",
            "🏆 llama3.2:3b ชนะเลิศความคุ้มค่ารวม (Suitability = 87.70): ตอบเร็วขึ้น 3.4 เท่า (5.60s / 47.6 TPS) และเก็บคำสำคัญได้ 86.7% เท่ากับ gemma3:4b ส่วน qwen2.5:3b ปั่นเร็วถึง 60.0 TPS",
        ],
        [
            8,
            "โมเดล LLM แนะนำสำหรับโหมดคุณภาพวิชาการสูงสุด (Academic Quality Mode)",
            "gemma3:4b",
            "gemma3:4b (3.3 GB)",
            "OLLAMA_MODEL=gemma3:4b",
            "ใช้เป็น Baseline หลักเพราะขนาด 3.3 GB พอดีเพดาน VRAM 4GB และเก่งภาษาไทย",
            "🏅 gemma3:4b ชนะเลิศด้านคุณภาพเนื้อหาสูงสุด (Quality = 84.67): เรียบเรียงภาษาไทย ตารางเปรียบเทียบ Markdown และอ้างอิงวิชาการได้สละสลวยและละเอียดที่สุด",
        ],
    ]
    for c_idx, h in enumerate(headers_2, start=1):
        ws2.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_2, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws2.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws2,
        4,
        4 + len(rows_2),
        len(headers_2),
        highlight_rows=set(range(5, 5 + len(rows_2))),
        left_cols=(2, 4, 5, 6, 7),
        code_cols=(5,),
    )
    auto_fit_sheet(ws2, max_width=54)

    # -------------------------------------------------------------------------
    # SHEET 3: Exact Backend Code Changes Guide
    # -------------------------------------------------------------------------
    ws3 = wb.create_sheet(title="03_Backend_Code_Changes")
    ws3["A1"] = "💻 คู่มือแก้ไขโค้ดฝั่ง Backend (FastAPI) แบบระบุไฟล์ บรรทัด และโค้ดที่ต้องใส่"
    ws3["A1"].font = TITLE_FONT
    ws3["A2"] = "ทีม Backend สามารถคัดลอกโค้ดด้านล่างไปอัปเดตตามไฟล์ที่ระบุเพื่อเปิดใช้งานฟีเจอร์ทั้งหมดที่ฝั่ง RAG เตรียมไว้ให้"
    ws3["A2"].font = SUBTITLE_FONT

    headers_3 = [
        "ลำดับ",
        "ไฟล์ที่ต้องแก้ไข / สร้าง (File Path)",
        "ตำแหน่งบรรทัด / ฟังก์ชัน",
        "ปัญหาในโค้ดปัจจุบัน (Current Limitation)",
        "โค้ดที่ต้องแก้ไข / เพิ่มเติม (Exact Code Snippet to Apply)",
    ]
    rows_3 = [
        [
            1,
            "backend/app/schemas/chat.py",
            "Class ChatRequest (บรรทัด 10-25)\n& Class ChatResponse (บรรทัด 51-59)",
            "ChatRequest ยังไม่รับ llm_model, llm_provider, profile_name และ ChatResponse ยังไม่ส่งค่า model และ performance (TPS / Tokens) กลับไปให้ Frontend",
            "class ChatRequest(BaseModel):\n"
            "    workspace_id: str | None = None\n"
            "    query_text: str\n"
            "    messages: list[ChatMessage] = Field(default_factory=list)\n"
            "    parent_query_id: int | None = None\n"
            "    llm_provider: str | None = Field(default=None, description='ollama หรือ groq')\n"
            "    llm_model: str | None = Field(default=None, description='เช่น llama3.2:3b, gemma3:4b, qwen2.5:3b')\n"
            "    profile_name: str | None = Field(default=None, description='ชื่อโปรไฟล์พารามิเตอร์ RAG')\n\n"
            "class ChatResponse(BaseModel):\n"
            "    ...\n"
            "    model: str | None = None\n"
            "    performance: dict | None = None",
        ],
        [
            2,
            "backend/app/services/rag_services.py",
            "ฟังก์ชัน process_rag_query (บรรทัด 119-183)\nและ process_rag_stream (บรรทัด 185-270)",
            "เรียก answer_question() และ stream_answer_question() โดยไม่ได้ส่ง llm_provider, llm_model, config เข้าไป และไม่ได้ดึง rag_output.get('performance') ส่งกลับ",
            "from app.rag.retrieval.rag_config import get_config_by_name, get_active_rag_config\n\n"
            "cfg = get_config_by_name(profile_name) if profile_name else get_active_rag_config()\n"
            "rag_output = answer_question(\n"
            "    query_text,\n"
            "    session_id=active_workspace_id,\n"
            "    llm_provider=llm_provider,\n"
            "    llm_model=llm_model,\n"
            "    config=cfg,\n"
            ")\n"
            "# และใน stream_answer_question:\n"
            "events = stream_answer_question(\n"
            "    question=query_text,\n"
            "    session_id=active_workspace_id,\n"
            "    llm_provider=llm_provider,\n"
            "    llm_model=llm_model,\n"
            "    config=cfg,\n"
            ")",
        ],
        [
            3,
            "backend/app/api/v1/chat.py",
            "ฟังก์ชัน query_rag (บรรทัด 38-55)\nและ query_rag_stream (บรรทัด 61-87)",
            "ยังไม่ได้ส่ง request.llm_provider, request.llm_model, request.profile_name เข้าไปใน process_rag_query และ process_rag_stream",
            "return await run_in_threadpool(\n"
            "    process_rag_query,\n"
            "    db=db,\n"
            "    query_text=request.query_text,\n"
            "    workspace_id=request.workspace_id,\n"
            "    parent_query_id=request.parent_query_id,\n"
            "    messages=request.messages,\n"
            "    llm_provider=request.llm_provider,\n"
            "    llm_model=request.llm_model,\n"
            "    profile_name=request.profile_name,\n"
            ")",
        ],
        [
            4,
            "backend/app/api/v1/ai_config.py (สร้างไฟล์ใหม่)\nและผูกใน backend/app/api/v1/router.py",
            "Router ใหม่ `/api/v1/rag-config`",
            "ฝั่ง RAG มีระบบปรับพารามิเตอร์อิสระ เซฟเป็นชื่อใหม่ และรันเปรียบเทียบโปรไฟล์เก่า-ใหม่ใน rag_config.py และ config_benchmark.py แล้ว แต่ยังไม่มี API Route",
            "from fastapi import APIRouter\n"
            "from app.rag.retrieval.rag_config import (\n"
            "    list_all_configs, get_active_rag_config, save_custom_config,\n"
            "    set_active_rag_config_by_name, delete_custom_config\n"
            ")\n"
            "from app.rag.evaluation.config_benchmark import compare_two_configs\n\n"
            "router = APIRouter(prefix='/rag-config', tags=['RAG Parameter Studio'])\n"
            "@router.get('/profiles')\n"
            "def get_profiles():\n"
            "    return {'active': get_active_rag_config().to_dict(), 'profiles': list_all_configs()}\n\n"
            "@router.post('/profiles')\n"
            "def create_or_update_profile(profile_name: str, overrides: dict, base_preset: str = 'balanced_default', set_active: bool = True):\n"
            "    cfg = save_custom_config(profile_name, overrides, base_preset=base_preset, set_active=set_active)\n"
            "    return cfg.to_dict()",
        ],
        [
            5,
            "backend/app/api/v1/dashboard.py",
            "เพิ่ม Endpoint `/api/v1/dashboard/rag-benchmark`",
            "หน้า Admin Dashboard ยังไม่มี Endpoint สำหรับดึงผลลัพธ์การจูนพารามิเตอร์และตารางเปรียบเทียบโมเดล LLM ทั้ง 7 รุ่นไปแสดงผล",
            "@router.get('/rag-benchmark')\n"
            "def get_rag_benchmark_results():\n"
            "    import json, os\n"
            "    path = os.path.join('backend', 'app', 'rag', 'evaluation', 'results', 'parameter_sweep_results.json')\n"
            "    with open(path, 'r', encoding='utf-8') as f:\n"
            "        return json.load(f)",
        ],
    ]
    for c_idx, h in enumerate(headers_3, start=1):
        ws3.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_3, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws3.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws3,
        4,
        4 + len(rows_3),
        len(headers_3),
        highlight_rows={5, 6, 7},
        warn_rows={8, 9},
        left_cols=(2, 3, 4, 5),
        code_cols=(2, 5),
    )
    auto_fit_sheet(ws3, max_width=62)

    # -------------------------------------------------------------------------
    # SHEET 4: Complete API Endpoints Contract for Frontend & Backend
    # -------------------------------------------------------------------------
    ws4 = wb.create_sheet(title="04_New_API_Endpoints_Spec")
    ws4["A1"] = "🔌 สเปก API Endpoints ทั้งหมดที่เกี่ยวข้องกับระบบ RAG, การสลับโมเดล LLM และการปรับจูนพารามิเตอร์"
    ws4["A1"].font = TITLE_FONT
    ws4["A2"] = "ใช้เป็นข้อตกลงร่วมกัน (API Contract) ระหว่างทีม Backend และทีม Frontend"
    ws4["A2"].font = SUBTITLE_FONT

    headers_4 = [
        "Method & Path",
        "สถานะปัจจุบัน",
        "หน้าที่ของ Endpoint",
        "Request Body / Query Params",
        "Response JSON ตัวอย่าง",
        "ฟังก์ชันฝั่ง RAG ที่เรียกใช้",
    ]
    rows_4 = [
        [
            "GET /api/v1/chat/llm-profiles",
            "✅ มีอยู่แล้วใน chat.py (อัปเดตเพิ่มครบ 7 โมเดลแล้ว)",
            "ดึงรายชื่อโมเดล LLM ทั้งหมด (ทั้ง Local Ollama 7 รุ่น และ Groq Cloud) พร้อมโมเดลที่กำลังใช้งานอยู่",
            "ไม่มี (No Params)",
            '{\n  "active_provider": "ollama",\n  "active_model": "llama3.2:3b",\n  "profiles": [\n    {"id": "ollama_llama3_2_3b", "provider": "ollama", "model": "llama3.2:3b", "label": "Ollama - Llama 3.2 (3B) [2.0GB VRAM - Fast]"},\n    {"id": "ollama_gemma3_4b", "provider": "ollama", "model": "gemma3:4b", "label": "Ollama - Gemma 3 (4B) [3.3GB VRAM - Balanced]"},\n    {"id": "ollama_qwen2_5_3b", "provider": "ollama", "model": "qwen2.5:3b", "label": "Ollama - Qwen 2.5 (3B) [1.9GB VRAM - Ultra Fast]"}\n  ]\n}',
            "app.rag.retrieval.llm_provider.AVAILABLE_LLM_PROFILES\n& get_active_llm()",
        ],
        [
            "POST /api/v1/chat/set-active-llm",
            "✅ มีอยู่แล้วใน chat.py",
            "สลับโมเดล LLM หลักของระบบแบบ Runtime ทันทีโดยไม่ต้องรีสตาร์ทเซิร์ฟเวอร์",
            "Query Params:\nprovider=ollama\nmodel=llama3.2:3b",
            '{\n  "message": "Successfully switched active LLM to ollama (llama3.2:3b)",\n  "active_provider": "ollama",\n  "active_model": "llama3.2:3b"\n}',
            "app.rag.retrieval.llm_provider.set_active_llm(provider, model)",
        ],
        [
            "POST /api/v1/chat/query-stream",
            "🔧 ต้องอัปเดตเพิ่มฟิลด์ Optional (ACT-01)",
            "ยิงคำถามแชทแบบ Streaming (SSE) พร้อมระบุโมเดลหรือโปรไฟล์พารามิเตอร์รายคำถามได้",
            '{\n  "workspace_id": "ws-123",\n  "query_text": "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",\n  "messages": [],\n  "llm_provider": "ollama",\n  "llm_model": "llama3.2:3b",\n  "profile_name": "optimal_tuned"\n}',
            'SSE Event 1..N (answer_chunk):\ndata: {"type": "answer_chunk", "content": "1. **The LoRaWAN**..."}\n\nSSE Event สุดท้าย (metadata):\ndata: {"type": "metadata", "citations": [...], "timing": {...}, "performance": {"gen_speed_tps": 47.6, "input_tokens": 1519, "output_tokens": 93}, "model": "ollama (llama3.2:3b)"}',
            "app.rag.retrieval.prompt.stream_answer_question()",
        ],
        [
            "GET /api/v1/rag-config/profiles",
            "🆕 แนะนำให้เพิ่มใน ai_config.py (ACT-04)",
            "ดึงรายการโปรไฟล์พารามิเตอร์ทั้งหมด (Built-in Presets + Custom Saved Profiles) และโปรไฟล์ที่กำลังเปิดใช้งาน",
            "ไม่มี (No Params)",
            '{\n  "active_profile": "optimal_tuned",\n  "active_config": {"top_k": 15, "rerank_top_n": 10, "max_context_chunks": 6, "max_chunks_per_project": 2, "enable_hybrid": true, ...},\n  "all_profiles": { ... }\n}',
            "app.rag.retrieval.rag_config.list_all_configs()\n& get_active_rag_config()",
        ],
        [
            "POST /api/v1/rag-config/profiles",
            "🆕 แนะนำให้เพิ่มใน ai_config.py (ACT-04)",
            "ปรับค่าพารามิเตอร์แบบอิสระ (หรือเปิด/ปิดสวิตช์โมดูล) แล้วบันทึกเป็นโปรไฟล์ชื่อใหม่ลงไฟล์ custom_rag_configs.json",
            '{\n  "profile_name": "my_fast_test_v1",\n  "base_preset": "balanced_default",\n  "set_active": true,\n  "overrides": {\n    "top_k": 15,\n    "rerank_top_n": 10,\n    "max_context_chunks": 6,\n    "max_chunks_per_project": 2,\n    "enable_hybrid": true,\n    "enable_reranker": true,\n    "enable_boilerplate_filter": true,\n    "llm_model": "llama3.2:3b"\n  }\n}',
            '{\n  "profile_name": "my_fast_test_v1",\n  "top_k": 15,\n  "rerank_top_n": 10,\n  "max_context_chunks": 6,\n  "llm_model": "llama3.2:3b",\n  "status": "saved_and_activated"\n}',
            "app.rag.retrieval.rag_config.save_custom_config()",
        ],
        [
            "POST /api/v1/rag-config/compare",
            "🆕 แนะนำให้เพิ่มใน ai_config.py (ACT-04)",
            "ทดสอบยิงคำถามเปรียบเทียบโปรไฟล์พารามิเตอร์เก่า (Config A) กับโปรไฟล์ที่ปรับใหม่ (Config B) แบบ Side-by-Side",
            '{\n  "query": "เปรียบเทียบโครงงาน The LoRaWAN กับ BSLD",\n  "config_a": "legacy_unfiltered",\n  "config_b": "optimal_tuned"\n}',
            '{\n  "query": "...",\n  "config_a_result": {"quality_score": 62.0, "total_seconds": 18.2, "answer": "..."},\n  "config_b_result": {"quality_score": 85.0, "total_seconds": 5.3, "answer": "..."},\n  "deltas": {"quality_score_diff": +23.0, "winner": "optimal_tuned"}\n}',
            "app.rag.evaluation.config_benchmark.compare_two_configs()",
        ],
    ]
    for c_idx, h in enumerate(headers_4, start=1):
        ws4.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_4, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws4.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws4,
        4,
        4 + len(rows_4),
        len(headers_4),
        highlight_rows={5, 6, 7},
        warn_rows={8, 9, 10},
        left_cols=(1, 2, 3, 4, 5, 6),
        code_cols=(1, 4, 5, 6),
    )
    auto_fit_sheet(ws4, max_width=58)

    # -------------------------------------------------------------------------
    # SHEET 5: Frontend UI Components & UX Specification
    # -------------------------------------------------------------------------
    ws5 = wb.create_sheet(title="05_Frontend_UI_Components")
    ws5["A1"] = "🎨 รายการอัปเดตหน้าจอฝั่ง Frontend (UI Components & UX Guidelines)"
    ws5["A1"].font = TITLE_FONT
    ws5["A2"] = "รายละเอียด Component ที่ทีม Frontend ต้องอัปเดตเพื่อให้รองรับฟีเจอร์ใหม่ของระบบ RAGcoon"
    ws5["A2"].font = SUBTITLE_FONT

    headers_5 = [
        "ลำดับ",
        "ชื่อ Component / หน้าจอ",
        "ตำแหน่งบน UI",
        "ฟีเจอร์และการแสดงผลที่ต้องทำ (UI/UX Requirements)",
        "ข้อมูลจาก API ที่ใช้แสดงผล (Data Binding)",
    ]
    rows_5 = [
        [
            1,
            "LLM Model Selector (ตัวเลือกโมเดล 7 รุ่น)",
            "แถบด้านบนของหน้าแชท (Chat Header) หรือแถบข้างช่องพิมพ์คำถาม",
            "แสดง Dropdown ให้ผู้ใช้เลือกสลับโมเดลได้ตามต้องการ พร้อมแสดงป้ายกำกับ (Badge) บอกจุดเด่นจากการทดลองจริง:\n"
            "- 🏆 llama3.2:3b (2.0 GB) — แนะนำอันดับ 1: เร็ว 47.6 TPS + แม่นยำสูง (Suitability 87.7)\n"
            "- ⚡ qwen2.5:3b (1.9 GB) — แนะนำอันดับ 2: เร็วพิเศษ 60.0 TPS ประหยัด VRAM\n"
            "- 🏅 gemma3:4b (3.3 GB) — แชมป์คุณภาพภาษาไทยและตาราง Markdown (Quality 84.7)\n"
            "- 🚀 gemma3:1b (0.8 GB) — โหมดเบาพิเศษ 130.7 TPS\n"
            "- 🧠 qwen3:4b / qwen2.5:7b / llama3.1:8b — โมเดลทางเลือก",
            "ดึงรายการจาก `GET /api/v1/chat/llm-profiles`\nเมื่อเปลี่ยนค่า ให้เรียก `POST /api/v1/chat/set-active-llm` หรือส่ง `llm_model` ใน `POST /api/v1/chat/query-stream`",
        ],
        [
            2,
            "Performance & Token Metrics Pill (ป้ายแสดงความเร็วและ Token)",
            "มุมขวาล่างของกล่องข้อความคำตอบ AI (AI Message Footer)",
            "แสดงข้อมูลประสิทธิภาพการประมวลผลในแต่ละคำตอบ (สามารถคลิกดู Tooltip แยกส่วนได้):\n"
            "- ความเร็วสร้างคำตอบ: `⚡ 47.6 TPS`\n"
            "- เวลารวมแยกส่วน: `⏱️ รวม 5.3s (ค้นหา 0.31s | Rerank 0.18s | LLM 4.81s)`\n"
            "- ปริมาณ Token: `🪙 Input 1,519 / Output 93 tokens`\n"
            "- ชื่อโมเดลที่ตอบ: `🤖 llama3.2:3b`",
            "อ่านจาก SSE event `metadata` ฟิลด์ `timing`, `performance.gen_speed_tps`, `performance.input_tokens`, `performance.output_tokens`, `performance.token_breakdown`, และ `model`",
        ],
        [
            3,
            "Enhanced Citation Card (การ์ดเอกสารอ้างอิงหลายหน้า)",
            "ส่วนรายการเอกสารอ้างอิงใต้คำตอบ AI",
            "อัปเดตการ์ดอ้างอิงให้แสดงข้อมูลครบถ้วนตามโครงสร้างใหม่:\n"
            "- ชื่อโครงงาน (`project_title`) และปีการศึกษา (`year`)\n"
            "- เลขหน้าที่อ้างอิงรวม (`pages_formatted` เช่น `หน้า 17, 18, 22` แทนการโชว์แค่หน้าเดียว)\n"
            "- ชื่อผู้จัดทำ (`author`) และอาจารย์ที่ปรึกษา (`advisor`)\n"
            "- ปุ่มคลิกเปิดดูไฟล์ PDF ตรงไปยังหน้าที่อ้างอิง (`#page={page}`)",
            "อ่านจาก `citations[]` ใน SSE `metadata` event:\n`project_title`, `source`, `page`, `pages_formatted`, `author`, `advisor`, `year`, `document_id`",
        ],
        [
            4,
            "Admin RAG Parameter Studio (หน้าปรับจูนพารามิเตอร์อิสระ)",
            "เมนู Admin Settings -> AI / RAG Configuration",
            "หน้าตั้งค่าสำหรับผู้ดูแลระบบ:\n"
            "- Sliders ปรับค่า: `top_k` (5–100, แนะนำ 15), `rerank_top_n` (1–30, แนะนำ 10), `max_context_chunks` (2–15, แนะนำ 6), `max_chunks_per_project` (1–6, แนะนำ 2), `temperature` (0.0–1.0, แนะนำ 0.0)\n"
            "- Switch Toggles เปิด/ปิดโมดูลอิสระ: `Hybrid Search (BM25+E5)`, `Cross-Encoder Reranker`, `Boilerplate Noise Filter`, `Fast-Path Metadata`\n"
            "- ช่องตั้งชื่อโปรไฟล์ใหม่ + ปุ่ม **'บันทึกเป็นโปรไฟล์ใหม่ (Save Custom Profile)'**",
            "เชื่อมกับ `GET /api/v1/rag-config/profiles` และ `POST /api/v1/rag-config/profiles`",
        ],
        [
            5,
            "A/B Config & Benchmark Comparison View (หน้าทดสอบเทียบค่าเก่า-ใหม่)",
            "เมนู Admin -> Benchmark / Compare",
            "ให้ผู้ดูแลเลือกโปรไฟล์ A (เช่น ค่าเก่า) เทียบกับโปรไฟล์ B (เช่น ค่าที่ปรับใหม่) พิมพ์คำถามทดสอบ แล้วแสดงผลลัพธ์เปรียบเทียบซ้าย-ขวา พร้อมคะแนนตามกฎ Rule 1-7 (Citation, Cleanliness, Latency, Completeness, Key Phrase Recall)",
            "เชื่อมกับ `POST /api/v1/rag-config/compare` และ `GET /api/v1/dashboard/rag-benchmark`",
        ],
    ]
    for c_idx, h in enumerate(headers_5, start=1):
        ws5.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_5, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws5.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws5,
        4,
        4 + len(rows_5),
        len(headers_5),
        highlight_rows={5, 6, 7},
        warn_rows={8, 9},
        left_cols=(2, 3, 4, 5),
        code_cols=(5,),
    )
    auto_fit_sheet(ws5, max_width=56)

    # -------------------------------------------------------------------------
    # SHEET 6: Docker & Environment Setup (RTX 3050 Ti 4GB VRAM)
    # -------------------------------------------------------------------------
    ws6 = wb.create_sheet(title="06_Docker_And_Env_Setup")
    ws6["A1"] = "🐳 การตั้งค่า Docker Compose และ Environment Variables สำหรับโมเดล LLM ทั้ง 7 รุ่น"
    ws6["A1"].font = TITLE_FONT
    ws6["A2"] = "อัปเดตไฟล์ docker-compose.yml ให้เรียบร้อยแล้ว พร้อมคำแนะนำการรันบนเครื่องที่มีการ์ดจอ NVIDIA 4GB VRAM"
    ws6["A2"].font = SUBTITLE_FONT

    headers_6 = [
        "หัวข้อ (Configuration Area)",
        "ไฟล์ที่เกี่ยวข้อง",
        "สถานะ",
        "รายละเอียดและการตั้งค่าที่แนะนำ (Recommended Setting & Command)",
        "หมายเหตุสำหรับเครื่อง RTX 3050 Ti (4GB VRAM) + RAM 16GB",
    ]
    rows_6 = [
        [
            "1. บริการ Ollama Container ใน Docker",
            "docker-compose.yml (บรรทัด 40-72)",
            "✅ อัปเดตให้แล้ว",
            "ตั้งค่า entrypoint ของบริการ `ollama` ให้รัน `ollama serve` และตรวจสอบ/ดึงโมเดลหลักอัตโนมัติ:\n"
            "- gemma3:4b (3.3 GB)\n"
            "- qwen3:4b (2.5 GB)\n"
            "- qwen2.5:3b (1.9 GB)\n"
            "- llama3.2:3b (2.0 GB)\n"
            "- gemma3:1b (0.8 GB)\n"
            "- qwen2.5:7b (4.7 GB)",
            "ใช้ Docker Volume `ollama_data:/root/.ollama` ทำให้โหลดโมเดลเพียงครั้งแรกครั้งเดียว เมื่อปิด-เปิด Container ใหม่ไม่ต้องดาวน์โหลดซ้ำ",
        ],
        [
            "2. การตั้งค่าตัวแปรแวดล้อม (.env)",
            "backend/.env",
            "🔧 ตรวจสอบให้ตรงกัน",
            "OLLAMA_BASE_URL=http://localhost:11434 (หรือ http://ollama:11434 เมื่อรันใน Docker)\n"
            "OLLAMA_MODEL=llama3.2:3b  # หรือ gemma3:4b\n"
            "RAG_TOP_K=15\n"
            "RAG_RERANK_TOP_N=10\n"
            "RAG_MAX_CONTEXT_CHUNKS=6",
            "หากต้องการความเร็วตอบเฉลี่ย 5.6 วินาที แนะนำตั้ง `OLLAMA_MODEL=llama3.2:3b` หรือ `qwen2.5:3b` หากต้องการงานเขียนภาษาไทยละเอียดสูงสุดตั้ง `OLLAMA_MODEL=gemma3:4b`",
        ],
        [
            "3. การสลับ Chat Prompt Template อัตโนมัติตามตระกูลโมเดล",
            "backend/app/rag/retrieval/prompt.py\n& llm_provider.py",
            "✅ อัปเดตให้แล้ว",
            "ระบบตรวจจับชื่อโมเดลอัตโนมัติ:\n"
            "- ตระกูล `gemma*` -> ใช้ `<start_of_turn>user...<start_of_turn>model`\n"
            "- ตระกูล `llama*` -> ใช้ `<|begin_of_text|><|start_header_id|>system...`\n"
            "- ตระกูล `qwen2*` -> ใช้ `<|im_start|>system...<|im_start|>assistant` (ไม่มี `<think>`)\n"
            "- ตระกูล `qwen3*` -> ใช้ ChatML พร้อมปิดโหมดคิดยาว `<think>\\n</think>`",
            "ทำให้เมื่อผู้ใช้หรือ Frontend สลับโมเดลไปมาระหว่าง Gemma, Llama และ Qwen คำตอบจะไม่เพี้ยนและไม่มีแท็กหลุดออกมาในหน้าแชท",
        ],
    ]
    for c_idx, h in enumerate(headers_6, start=1):
        ws6.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_6, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws6.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws6,
        4,
        4 + len(rows_6),
        len(headers_6),
        highlight_rows={5, 7},
        warn_rows={6},
        left_cols=(1, 2, 4, 5),
        code_cols=(2, 4),
    )
    auto_fit_sheet(ws6, max_width=58)

    # -------------------------------------------------------------------------
    # SHEET 7: QA & Integration Acceptance Checklist
    # -------------------------------------------------------------------------
    ws7 = wb.create_sheet(title="07_Acceptance_Checklist")
    ws7["A1"] = "✅ เช็กลิสต์ตรวจรับการเชื่อมต่อระบบ (Backend & Frontend Integration QA Checklist)"
    ws7["A1"].font = TITLE_FONT
    ws7["A2"] = "ใช้ตรวจสอบความถูกต้องหลังทีม Backend และ Frontend อัปเดตโค้ดเสร็จสิ้น"
    ws7["A2"].font = SUBTITLE_FONT

    headers_7 = [
        "รหัสทดสอบ (Test ID)",
        "ฝั่งที่ทดสอบ",
        "สถานการณ์ทดสอบ (Test Scenario)",
        "ขั้นตอนการทดสอบ (Steps)",
        "ผลลัพธ์ที่ต้องได้ (Expected Result)",
    ]
    rows_7 = [
        [
            "QA-01",
            "Frontend + Backend",
            "ทดสอบสลับโมเดลเป็น llama3.2:3b และ qwen2.5:3b แล้วถามคำถามฮาร์ดแวร์",
            "1. เลือกโมเดล `llama3.2:3b` บนหน้าเว็บ\n2. ถามว่า 'โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง'",
            "ระบบตอบกลับภายใน ~5-7 วินาที ระบุโครงงาน The LoRaWAN พร้อมอ้างอิงหน้า 18 และใน metadata แสดง `\"model\": \"ollama (llama3.2:3b)\"`",
        ],
        [
            "QA-02",
            "Frontend + Backend",
            "ทดสอบคำถามเปรียบเทียบ 2 โครงงาน (พิสูจน์ Fair Quota = 2 Chunks/โปรเจกต์)",
            "ถามว่า 'เปรียบเทียบโครงงาน The LoRaWAN กับโครงงาน Beacon Signal Location Device ในด้านฮาร์ดแวร์'",
            "ระบบดึงเอกสารของทั้ง 2 โครงงานมาแสดงในตารางเปรียบเทียบครบถ้วน และในการ์ดอ้างอิงด้านล่างมีทั้งไฟล์ของ The LoRaWAN และไฟล์ 4_BSLD_Project.pdf",
        ],
        [
            "QA-03",
            "Frontend + Backend",
            "ทดสอบคำถามหมวดอาจารย์ที่ปรึกษา (พิสูจน์ Fast-Path Metadata < 0.3 วินาที)",
            "ถามว่า 'ใครเป็นที่ปรึกษาของ The LoRaWAN'",
            "ระบบตอบกลับทันทีในเวลา < 0.3 วินาที ว่า Asst. Prof. Dr. Suppakarn Chansareewittaya พร้อมรายชื่อกรรมการสอบและปีการศึกษา",
        ],
        [
            "QA-04",
            "Frontend + Backend",
            "ทดสอบคำถามหลอกถามสิ่งที่ไม่มีในเอกสาร (พิสูจน์ Anti-Hallucination Guard)",
            "ถามว่า 'โครงงาน The LoRaWAN มีการเชื่อมต่อกับ Line Notify หรือไม่'",
            "ระบบปฏิเสธอย่างชัดเจนว่าไม่พบข้อมูลการเชื่อมต่อกับ Line Notify ในเอกสาร (ไม่มั่วข้อมูลขึ้นมาเอง)",
        ],
        [
            "QA-05",
            "Admin Studio",
            "ทดสอบปรับค่าพารามิเตอร์อิสระและเซฟเป็นชื่อโปรไฟล์ใหม่",
            "ในหน้า Admin ปรับ `top_k=15, rerank_top_n=10, max_context_chunks=6` แล้วกดบันทึกชื่อ `custom_production_v1`",
            "โปรไฟล์ถูกบันทึกลง `custom_rag_configs.json` และปรากฏในรายการโปรไฟล์เมื่อรีเฟรชหน้าเว็บ",
        ],
    ]
    for c_idx, h in enumerate(headers_7, start=1):
        ws7.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows_7, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws7.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws7,
        4,
        4 + len(rows_7),
        len(headers_7),
        highlight_rows=set(range(5, 5 + len(rows_7))),
        left_cols=(3, 4, 5),
    )
    auto_fit_sheet(ws7, max_width=56)


def append_action_plan_to_existing_workbook(xlsx_path: str, sheet_title: str):
    if not os.path.exists(xlsx_path):
        return
    wb = load_workbook(xlsx_path)
    if sheet_title in wb.sheetnames:
        del wb[sheet_title]
    ws = wb.create_sheet(title=sheet_title)
    ws["A1"] = "🚀 แผนส่งมอบงานให้ทีม Backend & Frontend อัปเดตต่อ (Backend & Frontend Update Action Plan)"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = "สรุปรายการที่ทีม Backend (FastAPI) และทีม Frontend (UI) ต้องนำไปอัปเดตต่อหลังจากจบการจูนพารามิเตอร์และทดสอบ LLM ทั้ง 7 รุ่น"
    ws["A2"].font = SUBTITLE_FONT

    headers = [
        "รหัสงาน (Task ID)",
        "ความสำคัญ (Priority)",
        "ทีมรับผิดชอบ (Owner)",
        "หัวข้อสิ่งที่ต้องทำเพิ่ม (Action Item)",
        "ไฟล์ที่ต้องแก้ไข / สร้างเพิ่ม (Target Files)",
        "สาเหตุและสิ่งที่ฝั่ง RAG เตรียมไว้ให้แล้ว (Why Needed & What RAG Already Built)",
        "รายละเอียดการอัปเดตที่ต้องทำ (Exact Implementation Steps)",
    ]
    rows = build_action_plan_rows()
    for c_idx, h in enumerate(headers, start=1):
        ws.cell(row=4, column=c_idx, value=h)
    for r_offset, r_vals in enumerate(rows, start=5):
        for c_idx, v in enumerate(r_vals, start=1):
            ws.cell(row=r_offset, column=c_idx, value=v)
    style_sheet_table(
        ws,
        4,
        4 + len(rows),
        len(headers),
        highlight_rows={5, 6, 7},
        warn_rows={8, 9, 10, 11},
        left_cols=(4, 5, 6, 7),
        code_cols=(5,),
    )
    auto_fit_sheet(ws, max_width=54)
    wb.save(xlsx_path)


def build_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKEND_DATA_DIR, exist_ok=True)

    # 1. Create dedicated new file: RAGcoon_Backend_Frontend_Update_Handoff.xlsx
    wb_new = Workbook()
    populate_handoff_workbook(wb_new)
    out_new_1 = os.path.join(DATA_DIR, "RAGcoon_Backend_Frontend_Update_Handoff.xlsx")
    out_new_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Backend_Frontend_Update_Handoff.xlsx")
    wb_new.save(out_new_1)
    shutil.copyfile(out_new_1, out_new_2)
    print(f"Created new Handoff Excel ({len(wb_new.sheetnames)} sheets) -> {out_new_1}", flush=True)
    print(f"Created new Handoff Excel ({len(wb_new.sheetnames)} sheets) -> {out_new_2}", flush=True)

    # 2. Also append the Action Plan sheet into existing Parameter Tuning & Handoff workbooks
    param_1 = os.path.join(DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    param_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Parameter_Tuning_Experiments.xlsx")
    if os.path.exists(param_1):
        append_action_plan_to_existing_workbook(param_1, "12_Backend_Frontend_NextSteps")
        shutil.copyfile(param_1, param_2)
        print(f"Updated Parameter Tuning Excel with Sheet 12_Backend_Frontend_NextSteps -> {param_1}", flush=True)

    spec_1 = os.path.join(DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    spec_2 = os.path.join(BACKEND_DATA_DIR, "RAGcoon_Handoff_Specification.xlsx")
    if os.path.exists(spec_1):
        append_action_plan_to_existing_workbook(spec_1, "21_Backend_Frontend_NextSteps")
        shutil.copyfile(spec_1, spec_2)
        print(f"Updated Handoff Specification Excel with Sheet 21_Backend_Frontend_NextSteps -> {spec_1}", flush=True)


if __name__ == "__main__":
    build_all()
