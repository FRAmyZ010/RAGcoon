"""
Module: evaluate_ocr.py
Description:
    ระบบประเมินผลประสิทธิภาพของ Scan / OCR Text, Tables, Images และ Metadata แบบองค์รวม
    คำนวณ Exact Match, CER (Character Error Rate), WER (Word Error Rate),
    สถิติองค์ประกอบเอกสาร (ตาราง, รูปภาพ, Digital vs Scanned Pages),
    Data Completeness, Error Type Classification และสถิติ Processing Time (Mean, Median, P95)
    พร้อมทั้งมีเมนู Interactive ให้เลือกดูผลการประเมินแบบองค์รวมทีละไฟล์ (Comprehensive Inspection)
    สร้าง Excel Report หลาย Sheet และกราฟสรุปผล (Visualization Charts)

Usage:
    # 1. ใช้งานแบบ Interactive Menu (เลือกดูรายไฟล์ หรือประเมินทั้งหมด):
    python -m backend.app.rag.evaluation.evaluate_ocr

    # 2. รันการประเมินผลทั้งหมดทันที และสร้างไฟล์ Excel / กราฟสรุปผล:
    python -m backend.app.rag.evaluation.evaluate_ocr --all

    # 3. ระบุเลข PDF เพื่อดูผลเจาะลึกองค์รวมทันที:
    python -m backend.app.rag.evaluation.evaluate_ocr --select 1

    # 4. สร้างไฟล์ Template Ground Truth อัตโนมัติ:
    python -m backend.app.rag.evaluation.evaluate_ocr --generate-template
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

# Reconfigure stdout for Windows terminal compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import jiwer
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
from rapidfuzz import fuzz

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.embedding.pdf_scanning import scan_pdf_document


def normalize_ocr_text(text: str) -> str:
    """
    Text Normalization สำหรับการวัดผลแบบ Normalized:
    1. Unicode NFKC (แปลง ligatures เช่น fi, fl, ffi และ fullwidth chars)
    2. Lowercase
    3. ลบ Zero-width chars / Non-breaking spaces
    4. เชื่อมคำที่ถูก hyphen ตัดขึ้นบรรทัดใหม่
    5. ปรับ spacing และลบ leading/trailing spaces
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text).lower()
    norm = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0\u202f\u2007]", " ", norm)
    norm = re.sub(r"(\b[a-z]+)-\s*\n\s*([a-z]+\b)", r"\1\2", norm)
    norm = norm.replace("\r\n", "\n").replace("\r", "\n")
    norm = re.sub(r"[ \t]+", " ", norm)
    norm = re.sub(r"\n+", "\n", norm)
    return norm.strip()


def calculate_cer_wer(reference: str, hypothesis: str) -> tuple[float, float]:
    """คำนวณ Character Error Rate (CER) และ Word Error Rate (WER) ด้วย jiwer"""
    ref = reference.strip()
    hyp = hypothesis.strip()

    if not ref and not hyp:
        return 0.0, 0.0
    if not ref and hyp:
        return 100.0, 100.0
    if ref and not hyp:
        return 100.0, 100.0

    try:
        cer_val = jiwer.cer(ref, hyp) * 100.0
        wer_val = jiwer.wer(ref, hyp) * 100.0
        return min(cer_val, 100.0), min(wer_val, 100.0)
    except Exception:
        ratio = fuzz.ratio(ref, hyp)
        error_rate = max(0.0, 100.0 - ratio)
        return error_rate, error_rate


def classify_error_type(reference: str, hypothesis: str, cer: float, wer: float) -> str:
    """จัดกลุ่มประเภทข้อผิดพลาด (Error Categorization)"""
    ref = reference.strip()
    hyp = hypothesis.strip()

    if ref == hyp:
        return "No Error"
    if not hyp and ref:
        return "Empty OCR Result / Missing Text"
    if len(hyp) < len(ref) * 0.7:
        return "Truncated Text / Major Character Deletion"
    if len(hyp) > len(ref) * 1.3:
        return "Noise / Extra Characters Insertion"
    if cer <= 10.0 and wer > 0:
        return "Minor Character Error / Typo"
    if wer > 50.0:
        return "Wrong Words / High Substitution"
    return "Formatting / Spacing Mismatch"


def load_ocr_ground_truth(file_path: Path) -> list[dict[str, Any]]:
    """โหลดข้อมูล OCR Ground Truth จากไฟล์ JSON หรือ CSV"""
    if not file_path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ OCR Ground Truth ที่: {file_path}")

    if file_path.suffix.lower() == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        return df.to_dict(orient="records")
    else:
        raise ValueError("รองรับเฉพาะไฟล์ .json หรือ .csv")


def generate_ocr_ground_truth_template(pdf_dir: Path, output_file: Path, sample_pages: int | None = None) -> None:
    """
    สร้าง Template Ground Truth สำหรับทดสอบ OCR
    - หาก sample_pages เป็น None: สกัดและสร้าง Ground Truth ครบทุกหน้า 100% ทั้งเอกสาร (Full Document Benchmark)
    - หากระบุตัวเลข: สุ่มดึงตามจำนวนหน้าที่กำหนด
    """
    pdf_files = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.name.lower())
    template: list[dict[str, Any]] = []

    mode_text = f"{sample_pages} หน้าแรกต่อไฟล์" if sample_pages else "ครบทุกหน้า 100% (Full Document)"
    print(f"🔄 กำลังสร้าง OCR Ground Truth Template จาก {len(pdf_files)} ไฟล์ ({mode_text})...")

    for pdf_path in pdf_files:
        try:
            pages = scan_pdf_document(str(pdf_path))
            target_pages = pages if sample_pages is None else pages[:sample_pages]
            for p in target_pages:
                page_num = p["metadata"]["page_number"]
                content = p.get("content", "").strip()
                template.append({
                    "filename": pdf_path.name,
                    "page_number": page_num,
                    "ground_truth_text": content if content else "EMPTY_PAGE_OR_IMAGE",
                })
        except Exception as exc:
            template.append({
                "filename": pdf_path.name,
                "page_number": 1,
                "ground_truth_text": f"SCAN_ERROR: {exc}",
            })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"✅ บันทึก OCR Ground Truth Template เรียบร้อยแล้วที่: {output_file} (รวม {len(template)} หน้าทดสอบ)")


def analyze_pdf_document_elements(pdf_path: Path) -> dict[str, Any]:
    """สกัดและวิเคราะห์องค์ประกอบเอกสาร (ตาราง, รูปภาพ, หน้าสแกน, ตัวอักษร)"""
    total_tables = 0
    total_images = 0
    digital_pages = 0
    scanned_pages = 0
    page_elements = []

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            images = page.images or []
            raw_text = page.extract_text() or ""

            num_tables = len(tables)
            num_images = len(images)
            total_tables += num_tables
            total_images += num_images

            is_scanned = len(raw_text.strip()) < 15 and num_images > 0
            if is_scanned:
                scanned_pages += 1
            else:
                digital_pages += 1

            page_elements.append({
                "page_number": idx,
                "tables_count": num_tables,
                "images_count": num_images,
                "is_scanned": is_scanned,
                "chars_count": len(raw_text.strip()),
                "words_count": len(raw_text.strip().split()),
            })

    return {
        "total_tables": total_tables,
        "total_images": total_images,
        "digital_pages": digital_pages,
        "scanned_pages": scanned_pages,
        "page_elements": page_elements,
    }


def evaluate_single_ocr_pdf(
    pdf_path: Path,
    gt_by_file: dict[str, dict[int, str]],
    show_details: bool = True,
) -> dict[str, Any]:
    """ประเมินผล OCR และวิเคราะห์องค์ประกอบเอกสารแบบองค์รวมรายไฟล์ (Comprehensive Deep Inspection)"""
    filename = pdf_path.name
    file_gt = gt_by_file.get(filename, {})

    t_start = time.perf_counter()
    scan_error = None
    scanned_pages = []

    try:
        scanned_pages = scan_pdf_document(str(pdf_path))
    except Exception as exc:
        scan_error = str(exc)

    total_pdf_time = time.perf_counter() - t_start
    num_pages = len(scanned_pages)
    avg_page_time = total_pdf_time / num_pages if num_pages > 0 else 0.0

    # วิเคราะห์ตาราง รูปภาพ และหน้าสแกน
    try:
        elements_info = analyze_pdf_document_elements(pdf_path)
    except Exception:
        elements_info = {
            "total_tables": 0,
            "total_images": 0,
            "digital_pages": num_pages,
            "scanned_pages": 0,
            "page_elements": [],
        }

    page_rows = []
    file_norm_matches = 0
    file_exact_matches = 0
    file_cers = []
    file_wers = []
    file_sims = []
    total_chars_in_pdf = 0
    total_words_in_pdf = 0

    elem_map = {e["page_number"]: e for e in elements_info["page_elements"]}

    for p in scanned_pages:
        p_num = p["metadata"]["page_number"]
        ocr_raw = p.get("content", "").strip()
        total_chars_in_pdf += len(ocr_raw)
        total_words_in_pdf += len(ocr_raw.split())

        if p_num not in file_gt:
            continue

        gt_raw = file_gt[p_num]

        # Normalization
        gt_norm = normalize_ocr_text(gt_raw)
        ocr_norm = normalize_ocr_text(ocr_raw)

        exact_raw = 1 if gt_raw == ocr_raw else 0
        exact_norm = 1 if gt_norm == ocr_norm else 0

        if exact_norm == 1:
            file_norm_matches += 1
        if exact_raw == 1:
            file_exact_matches += 1

        cer, wer = calculate_cer_wer(gt_norm, ocr_norm)
        sim = fuzz.ratio(gt_norm, ocr_norm)
        completeness = 100.0 if ocr_raw else 0.0
        err_type = classify_error_type(gt_norm, ocr_norm, cer, wer)

        file_cers.append(cer)
        file_wers.append(wer)
        file_sims.append(sim)

        elem_p = elem_map.get(p_num, {"tables_count": 0, "images_count": 0, "is_scanned": False})

        page_rows.append({
            "Page": p_num,
            "Exact_Raw": "PASS" if exact_raw else "FAIL",
            "Exact_Norm": "PASS" if exact_norm else "FAIL",
            "CER": cer,
            "WER": wer,
            "Sim": sim,
            "Tables": elem_p["tables_count"],
            "Images": elem_p["images_count"],
            "Is_Scanned": "Yes" if elem_p["is_scanned"] else "No",
            "Completeness": completeness,
            "Error_Type": err_type,
            "GT_Preview": gt_raw[:60].replace("\n", " ").strip(),
            "OCR_Preview": ocr_raw[:60].replace("\n", " ").strip(),
        })

    n_samples = len(page_rows)
    avg_cer = float(np.mean(file_cers)) if n_samples else 0.0
    avg_wer = float(np.mean(file_wers)) if n_samples else 0.0
    avg_sim = float(np.mean(file_sims)) if n_samples else 0.0
    exact_rate = (file_norm_matches / n_samples * 100.0) if n_samples else 0.0

    meta = scanned_pages[0]["metadata"] if scanned_pages else {}

    if show_details:
        print("\n" + "=" * 92)
        print(f"🔍 รายละเอียดการวิเคราะห์แบบองค์รวม (Comprehensive PDF Document Inspection)")
        print(f"📄 ไฟล์: {filename}")
        print("=" * 92)
        print(f"📋 1. โครงสร้างและส่วนประกอบเอกสาร (Document Composition):")
        print(f"  • จำนวนหน้าทั้งหมด (Total Pages)      : {num_pages} หน้า")
        print(f"  • Digital Text Pages (มี Text Layer) : {elements_info['digital_pages']} หน้า ({(elements_info['digital_pages']/num_pages*100 if num_pages else 0):.1f}%)")
        print(f"  • Scanned Image Pages (ภาพสแกน)     : {elements_info['scanned_pages']} หน้า ({(elements_info['scanned_pages']/num_pages*100 if num_pages else 0):.1f}%)")
        print(f"  • ตารางที่ตรวจพบ (Tables Found)      : {elements_info['total_tables']} ตาราง")
        print(f"  • รูปภาพ/แผนภาพ (Images/Figures)     : {elements_info['total_images']} รูป")
        print(f"  • จำนวนตัวอักษรทั้งหมด (Total Chars)   : {total_chars_in_pdf:,} ตัวอักษร")
        print(f"  • จำนวนคำทั้งหมด (Total Words)       : {total_words_in_pdf:,} คำ")
        print("-" * 92)
        print(f"🎯 2. คุณภาพการอ่านข้อความ & OCR (OCR Text Quality):")
        print(f"  • Tested Ground Truth Pages         : {n_samples} หน้า")
        print(f"  • Exact Match Accuracy              : {file_norm_matches}/{n_samples} ({exact_rate:.2f}%)")
        print(f"  • Character Error Rate (CER)        : {avg_cer:.2f}%")
        print(f"  • Word Error Rate (WER)             : {avg_wer:.2f}%")
        print(f"  • Text Similarity (RapidFuzz)       : {avg_sim:.2f}%")
        print("-" * 92)
        print(f"🏷️ 3. ข้อมูล Metadata ของโครงงาน (Extracted Project Metadata):")
        print(f"  • Project Title : {meta.get('project_title') or '(None)'}")
        print(f"  • Author        : {meta.get('author') or '(None)'}")
        print(f"  • Advisor       : {meta.get('advisor') or '(None)'}")
        print(f"  • Academic Year : {meta.get('year') or '(None)'}")
        print(f"  • Keywords      : {meta.get('keywords') or '(None)'}")
        print("-" * 92)
        print(f"⚡ 4. ประสิทธิภาพและความเร็ว (Processing Performance):")
        print(f"  • Processing Time                   : {total_pdf_time:.3f} วินาที")
        print(f"  • Average Time per Page             : {avg_page_time:.4f} วินาที/หน้า")
        print(f"  • Scan Throughput                   : {(num_pages / total_pdf_time if total_pdf_time else 0):.2f} หน้า/วินาที")
        print("-" * 92)
        print(f"📑 5. รายละเอียดระดับหน้า (Sampled Page-by-Page OCR Table):")
        print(f"{'Page':<5} | {'Status':<7} | {'CER (%)':<8} | {'WER (%)':<8} | {'Tables':<6} | {'Images':<6} | {'OCR Preview'}")
        print("-" * 92)
        for row in page_rows:
            status_icon = "✅ PASS" if row["Exact_Norm"] == "PASS" else "❌ FAIL"
            print(f"{row['Page']:<5} | {status_icon:<7} | {row['CER']:7.2f}% | {row['WER']:7.2f}% | {row['Tables']:6d} | {row['Images']:6d} | {row['OCR_Preview'][:35]}")
        print("=" * 92)

    return {
        "filename": filename,
        "total_pages": num_pages,
        "total_tables": elements_info["total_tables"],
        "total_images": elements_info["total_images"],
        "digital_pages": elements_info["digital_pages"],
        "scanned_pages": elements_info["scanned_pages"],
        "total_characters": total_chars_in_pdf,
        "total_words": total_words_in_pdf,
        "tested_samples": n_samples,
        "exact_match_norm": exact_rate,
        "avg_cer": avg_cer,
        "avg_wer": avg_wer,
        "avg_sim": avg_sim,
        "processing_time": total_pdf_time,
        "time_per_page": avg_page_time,
        "page_rows": page_rows,
        "scan_error": scan_error,
    }


def evaluate_ocr_system(
    gt_list: list[dict[str, Any]],
    pdf_dir: Path,
    output_excel: Path | None = None,
    output_chart: Path | None = None,
) -> dict[str, Any]:
    """ประเมินผลความถูกต้องและประสิทธิภาพของระบบ Scan / OCR ทั้งหมด"""
    gt_by_file: dict[str, dict[int, str]] = {}
    for item in gt_list:
        fname = item["filename"]
        pnum = int(item["page_number"])
        gt_text = item.get("ground_truth_text", "")
        if fname not in gt_by_file:
            gt_by_file[fname] = {}
        gt_by_file[fname][pnum] = gt_text

    page_results: list[dict[str, Any]] = []
    pdf_summaries: list[dict[str, Any]] = []
    pdf_times: list[float] = []
    page_times: list[float] = []

    print("\n" + "=" * 80)
    print("🚀 เริ่มต้นการประเมินผล SCAN / OCR TEXT, TABLES & IMAGES BENCHMARK")
    print("=" * 80)

    pdf_files = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.name.lower())

    for idx, pdf_path in enumerate(pdf_files, start=1):
        filename = pdf_path.name
        if filename not in gt_by_file:
            continue

        res = evaluate_single_ocr_pdf(pdf_path, gt_by_file, show_details=False)
        pdf_times.append(res["processing_time"])
        num_pages = res["total_pages"]

        for row in res["page_rows"]:
            page_times.append(res["time_per_page"])
            page_results.append({
                "Filename": filename,
                "Page": row["Page"],
                "Ground_Truth_Raw": row["GT_Preview"],
                "OCR_Result_Raw": row["OCR_Preview"],
                "Exact_Match_Raw": row["Exact_Raw"],
                "Exact_Match_Norm": row["Exact_Norm"],
                "CER (%)": round(row["CER"], 2),
                "WER (%)": round(row["WER"], 2),
                "Similarity (%)": round(row["Sim"], 2),
                "Tables": row["Tables"],
                "Images": row["Images"],
                "Completeness (%)": row["Completeness"],
                "Error_Type": row["Error_Type"],
                "Page_Time (s)": round(res["time_per_page"], 4),
            })

        pdf_summaries.append({
            "Filename": filename,
            "Total_Pages": num_pages,
            "Tables_Count": res["total_tables"],
            "Images_Count": res["total_images"],
            "Digital_Pages": res["digital_pages"],
            "Scanned_Pages": res["scanned_pages"],
            "Total_Characters": res["total_characters"],
            "Total_Words": res["total_words"],
            "Evaluated_Pages": res["tested_samples"],
            "Exact_Match_Norm (%)": round(res["exact_match_norm"], 2),
            "Avg_CER (%)": round(res["avg_cer"], 2),
            "Avg_WER (%)": round(res["avg_wer"], 2),
            "Avg_Similarity (%)": round(res["avg_sim"], 2),
            "Processing_Time (s)": round(res["processing_time"], 3),
            "Time_Per_Page (s)": round(res["time_per_page"], 4),
        })

        print(
            f"[{idx:02d}] {filename[:32]:<32} | Pages:{num_pages:3d} | Tables:{res['total_tables']:2d} | Images:{res['total_images']:2d} | "
            f"Exact: {res['exact_match_norm']:5.1f}% | CER: {res['avg_cer']:4.1f}% | Time: {res['processing_time']:.2f}s"
        )

    if not page_results:
        print("❌ ไม่พบข้อมูลสำหรับประเมินผล")
        return {}

    df_pages = pd.DataFrame(page_results)
    df_pdfs = pd.DataFrame(pdf_summaries)

    total_pdfs = len(df_pdfs)
    total_eval_pages = len(df_pages)
    total_doc_pages = df_pdfs["Total_Pages"].sum()
    total_doc_tables = df_pdfs["Tables_Count"].sum()
    total_doc_images = df_pdfs["Images_Count"].sum()
    total_doc_chars = df_pdfs["Total_Characters"].sum()

    exact_match_rate = (df_pages["Exact_Match_Norm"] == "PASS").mean() * 100.0
    exact_match_raw_rate = (df_pages["Exact_Match_Raw"] == "PASS").mean() * 100.0
    avg_cer = df_pages["CER (%)"].mean()
    avg_wer = df_pages["WER (%)"].mean()
    avg_similarity = df_pages["Similarity (%)"].mean()
    avg_completeness = df_pages["Completeness (%)"].mean()

    avg_time_pdf = float(np.mean(pdf_times))
    avg_time_page = float(np.mean(page_times))
    min_time_page = float(np.min(page_times))
    max_time_page = float(np.max(page_times))
    med_time_page = float(np.median(page_times))
    p95_time_page = float(np.percentile(page_times, 95))

    print("\n" + "=" * 75)
    print("📊 SCAN / OCR COMPREHENSIVE EVALUATION SUMMARY")
    print("=" * 75)
    print(f"Total Evaluated PDFs        : {total_pdfs} เล่ม")
    print(f"Total Scanned Pages in PDFs : {total_doc_pages} หน้า")
    print(f"Total Sampled Pages Tested  : {total_eval_pages} หน้า")
    print(f"Total Tables Detected       : {total_doc_tables} ตาราง")
    print(f"Total Images/Figures Found  : {total_doc_images} รูป")
    print(f"Total Extracted Characters  : {total_doc_chars:,} ตัวอักษร")
    print("-" * 75)
    print(f"Exact Match (Normalized)    : {exact_match_rate:.2f}%")
    print(f"Exact Match (Raw)           : {exact_match_raw_rate:.2f}%")
    print(f"Average CER (Char Error)    : {avg_cer:.2f}% (ยิ่งต่ำยิ่งดี)")
    print(f"Average WER (Word Error)    : {avg_wer:.2f}% (ยิ่งต่ำยิ่งดี)")
    print(f"Average Text Similarity     : {avg_similarity:.2f}%")
    print(f"Data Completeness           : {avg_completeness:.2f}%")
    print("-" * 75)
    print(f"Average Time / PDF          : {avg_time_pdf:.3f} วินาที")
    print(f"Average Time / Page         : {avg_time_page:.4f} วินาที")
    print(f"Minimum Time / Page         : {min_time_page:.4f} วินาที")
    print(f"Maximum Time / Page         : {max_time_page:.4f} วินาที")
    print(f"Median Time / Page          : {med_time_page:.4f} วินาที")
    print(f"P95 Time / Page (95th %)    : {p95_time_page:.4f} วินาที")
    print(f"Overall Throughput          : {(1.0 / avg_time_page if avg_time_page else 0):.2f} หน้า/วินาที")
    print("=" * 75)

    errors_df = df_pages[df_pages["Exact_Match_Norm"] == "FAIL"]
    print(f"\n🔍 ERROR ANALYSIS ({len(errors_df)} รายการที่พบข้อผิดพลาด):")
    print("-" * 75)
    if not errors_df.empty:
        error_counts = errors_df["Error_Type"].value_counts()
        for etype, count in error_counts.items():
            pct = (count / len(errors_df)) * 100
            print(f"  • {etype:<40} : {count:2d} รายการ ({pct:5.1f}%)")
    else:
        print("  🎉 ยอดเยี่ยม! ไม่พบข้อผิดพลาดในข้อมูลที่ทดสอบ (100% Accuracy)")
    print("=" * 75)

    if output_excel:
        output_excel.parent.mkdir(parents=True, exist_ok=True)
        summary_kpis = [
            {"Metric": "Total Evaluated PDFs", "Value": str(total_pdfs)},
            {"Metric": "Total Scanned Pages in PDFs", "Value": str(total_doc_pages)},
            {"Metric": "Total Sampled Pages Tested", "Value": str(total_eval_pages)},
            {"Metric": "Total Tables Detected", "Value": str(total_doc_tables)},
            {"Metric": "Total Images / Figures Found", "Value": str(total_doc_images)},
            {"Metric": "Total Extracted Characters", "Value": f"{total_doc_chars:,}"},
            {"Metric": "Exact Match Accuracy (Normalized)", "Value": f"{exact_match_rate:.2f}%"},
            {"Metric": "Exact Match Accuracy (Raw)", "Value": f"{exact_match_raw_rate:.2f}%"},
            {"Metric": "Average CER (Character Error Rate)", "Value": f"{avg_cer:.2f}%"},
            {"Metric": "Average WER (Word Error Rate)", "Value": f"{avg_wer:.2f}%"},
            {"Metric": "Average Text Similarity", "Value": f"{avg_similarity:.2f}%"},
            {"Metric": "Data Completeness", "Value": f"{avg_completeness:.2f}%"},
            {"Metric": "Average Processing Time / PDF", "Value": f"{avg_time_pdf:.3f} sec"},
            {"Metric": "Average Processing Time / Page", "Value": f"{avg_time_page:.4f} sec"},
            {"Metric": "Median Processing Time / Page", "Value": f"{med_time_page:.4f} sec"},
            {"Metric": "P95 Processing Time / Page", "Value": f"{p95_time_page:.4f} sec"},
            {"Metric": "Throughput", "Value": f"{(1.0 / avg_time_page if avg_time_page else 0):.2f} pages/sec"},
        ]
        df_summary_kpi = pd.DataFrame(summary_kpis)
        time_stats_df = pd.DataFrame([
            {"Metric": "Mean (sec/page)", "Value": avg_time_page},
            {"Metric": "Min (sec/page)", "Value": min_time_page},
            {"Metric": "Max (sec/page)", "Value": max_time_page},
            {"Metric": "Median (sec/page)", "Value": med_time_page},
            {"Metric": "P95 (sec/page)", "Value": p95_time_page},
        ])

        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            df_summary_kpi.to_excel(writer, sheet_name="Summary", index=False)
            df_pdfs.to_excel(writer, sheet_name="PDF Summaries", index=False)
            df_pages.to_excel(writer, sheet_name="Page Results", index=False)
            if not errors_df.empty:
                errors_df.to_excel(writer, sheet_name="Errors", index=False)
            else:
                pd.DataFrame([{"Message": "No errors found"}]).to_excel(writer, sheet_name="Errors", index=False)
            time_stats_df.to_excel(writer, sheet_name="Processing Time", index=False)

        print(f"\n💾 บันทึก Excel Report เรียบร้อยแล้วที่: {output_excel}")

    if output_chart and not df_pdfs.empty:
        output_chart.parent.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("PDF Scan & OCR Evaluation Report Benchmark", fontsize=16, fontweight="bold")

        short_names = [f"PDF {i+1}" for i in range(len(df_pdfs))]
        axes[0, 0].bar(short_names, df_pdfs["Exact_Match_Norm (%)"], color="#2ecc71", edgecolor="#27ae60")
        axes[0, 0].set_title("Exact Match Accuracy (%) per PDF", fontweight="bold")
        axes[0, 0].set_ylim(0, 110)
        axes[0, 0].grid(axis="y", linestyle="--", alpha=0.7)

        # Tables & Images distribution
        x = np.arange(len(short_names))
        width = 0.35
        axes[0, 1].bar(x - width/2, df_pdfs["Tables_Count"], width, label="Tables", color="#9b59b6")
        axes[0, 1].bar(x + width/2, df_pdfs["Images_Count"], width, label="Images/Figures", color="#f39c12")
        axes[0, 1].set_title("Tables & Images/Figures Count per PDF", fontweight="bold")
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(short_names)
        axes[0, 1].legend()
        axes[0, 1].grid(axis="y", linestyle="--", alpha=0.7)

        axes[1, 0].plot(short_names, df_pdfs["Time_Per_Page (s)"], marker="o", color="#3498db", linewidth=2)
        axes[1, 0].set_title("Average Processing Time (sec/page)", fontweight="bold")
        axes[1, 0].set_ylabel("Seconds")
        axes[1, 0].grid(True, linestyle="--", alpha=0.7)

        if not errors_df.empty:
            err_counts = errors_df["Error_Type"].value_counts()
            axes[1, 1].pie(err_counts.values, labels=err_counts.index, autopct="%1.1f%%", startangle=140)
            axes[1, 1].set_title("Error Type Distribution", fontweight="bold")
        else:
            axes[1, 1].text(0.5, 0.5, "100% PASS\nNo Errors Found", ha="center", va="center", fontsize=14, color="#27ae60", fontweight="bold")
            axes[1, 1].set_title("Error Type Distribution", fontweight="bold")
            axes[1, 1].axis("off")

        plt.tight_layout()
        plt.savefig(output_chart, dpi=300)
        plt.close()
        print(f"📊 สร้างกราฟสรุปผล (Visualization Chart) เรียบร้อยแล้วที่: {output_chart}\n")

    return {
        "exact_match_rate": exact_match_rate,
        "avg_cer": avg_cer,
        "avg_wer": avg_wer,
        "avg_time_pdf": avg_time_pdf,
        "avg_time_page": avg_time_page,
    }


def interactive_ocr_menu(
    gt_list: list[dict[str, Any]],
    pdf_dir: Path,
    output_excel: Path,
    output_chart: Path,
) -> None:
    """เมนู Interactive ใน Terminal สำหรับเลือกดูผลการประเมิน OCR รายไฟล์"""
    pdf_files = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.name.lower())

    gt_by_file: dict[str, dict[int, str]] = {}
    for item in gt_list:
        fname = item["filename"]
        pnum = int(item["page_number"])
        gt_text = item.get("ground_truth_text", "")
        if fname not in gt_by_file:
            gt_by_file[fname] = {}
        gt_by_file[fname][pnum] = gt_text

    while True:
        print("\n" + "=" * 70)
        print("🔍 ระบบประเมินผล SCAN / OCR & DOCUMENT ELEMENTS (Comprehensive)")
        print("=" * 70)
        print("ตัวเลือกการทำงาน:")
        print("  [1] ประเมินผล OCR ทั้งหมด (Full Benchmark, Export Excel & Charts)")
        print("  [2] เลือกหมายเลข PDF เพื่อดูผลลัพธ์แบบองค์รวม (Inspect by Number)")
        print("  [3] สร้าง/อัปเดตไฟล์ Template OCR Ground Truth")
        print("  [q] ออกจากโปรแกรม (Exit)")
        print("-" * 70)

        choice = input("👉 กรุณาเลือกเมนู [1, 2, 3, q]: ").strip().lower()

        if choice == "1":
            evaluate_ocr_system(gt_list, pdf_dir, output_excel, output_chart)

        elif choice == "2":
            while True:
                print("\n" + "=" * 70)
                print(f"📁 รายการไฟล์ PDF สำหรับประเมินผล OCR ({len(pdf_files)} ไฟล์):")
                print("=" * 70)
                for idx, pdf in enumerate(pdf_files, start=1):
                    in_gt = "✓" if pdf.name in gt_by_file else " "
                    print(f"  [{idx:2d}] [{in_gt}] {pdf.name}")
                print("-" * 70)
                print("หมายเหตุ: [✓] หมายถึงมีข้อมูลอยู่ใน OCR Ground Truth")
                print("พิมพ์ 'b' เพื่อกลับสู่เมนูหลัก หรือ 'q' เพื่อออก")

                sel = input(f"\n👉 กรุณาใส่หมายเลข PDF (1-{len(pdf_files)}) : ").strip().lower()
                if sel == "b":
                    break
                if sel == "q":
                    print("👋 ออกจากโปรแกรมเรียบร้อยแล้ว")
                    return

                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(pdf_files):
                        target_pdf = pdf_files[num - 1]
                        evaluate_single_ocr_pdf(target_pdf, gt_by_file, show_details=True)
                        input("\nกด Enter เพื่อเลือกไฟล์อื่นต่อ...")
                    else:
                        print(f"⚠️ กรุณาใส่หมายเลขระหว่าง 1 ถึง {len(pdf_files)}")
                else:
                    print("⚠️ กรุณาใส่หมายเลขที่ถูกต้อง")

        elif choice == "3":
            generate_ocr_ground_truth_template(pdf_dir, PROJECT_ROOT / "backend" / "data" / "ocr_ground_truth.json")

        elif choice in ("q", "exit"):
            print("👋 ออกจากโปรแกรมเรียบร้อยแล้ว")
            break
        else:
            print("⚠️ กรุณาเลือกตัวเลือกที่ถูกต้อง (1, 2, 3 หรือ q)")


def main():
    parser = argparse.ArgumentParser(description="Dedicated Scan/OCR Text Quality and Performance Evaluation System.")
    parser.add_argument(
        "--gt",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "ocr_ground_truth.json",
        help="Path to OCR Ground Truth JSON or CSV file.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "files_for_evaluation",
        help="Directory containing the evaluation PDFs.",
    )
    parser.add_argument(
        "--output-excel",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "ocr_evaluation.xlsx",
        help="Path to save the multi-sheet Excel report.",
    )
    parser.add_argument(
        "--output-chart",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "ocr_evaluation_charts.png",
        help="Path to save the summary visualization chart PNG.",
    )
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Auto-generate a starter OCR Ground Truth template JSON from pdf-dir.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full benchmark immediately and export Excel + Charts.",
    )
    parser.add_argument(
        "--select",
        type=int,
        default=None,
        help="Inspect a specific PDF by index number (e.g. --select 1).",
    )

    args = parser.parse_args()

    if args.generate_template:
        generate_ocr_ground_truth_template(args.pdf_dir, args.gt)
        return

    if not args.gt.exists():
        print(f"⚠️ ไม่พบไฟล์ Ground Truth ที่: {args.gt}")
        print("💡 กำลังสร้างไฟล์ Template OCR Ground Truth เริ่มต้นให้...")
        generate_ocr_ground_truth_template(args.pdf_dir, args.gt)

    gt_list = load_ocr_ground_truth(args.gt)

    if args.select is not None:
        pdf_files = sorted(args.pdf_dir.glob("*.pdf"), key=lambda p: p.name.lower())
        if 1 <= args.select <= len(pdf_files):
            gt_by_file: dict[str, dict[int, str]] = {}
            for item in gt_list:
                fname = item["filename"]
                pnum = int(item["page_number"])
                gt_text = item.get("ground_truth_text", "")
                if fname not in gt_by_file:
                    gt_by_file[fname] = {}
                gt_by_file[fname][pnum] = gt_text
            evaluate_single_ocr_pdf(pdf_files[args.select - 1], gt_by_file, show_details=True)
        else:
            print(f"❌ หมายเลขไม่ถูกต้อง กรุณาเลือกหมายเลขระหว่าง 1 ถึง {len(pdf_files)}")
        return

    if args.all:
        evaluate_ocr_system(gt_list, args.pdf_dir, args.output_excel, args.output_chart)
        return

    interactive_ocr_menu(gt_list, args.pdf_dir, args.output_excel, args.output_chart)


if __name__ == "__main__":
    main()
