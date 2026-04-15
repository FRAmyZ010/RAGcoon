import pdfplumber
import os
from .metadata_extractor import extract_project_metadata

def scan_pdf_document(file_path):
    extracted_data = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        
        # 1. เตรียมตัวแปรเก็บ Metadata พิเศษ (ค่าเริ่มต้นเป็น None)
        special_meta = {
            "project_title": None, "author": None, 
            "advisor": None, "keywords": None, "year": None
        }

        # 2. Loop อ่านทุกหน้าตามปกติ
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=1, y_tolerance=2)

            if text:
                # 3. เฉพาะ 5 หน้าแรก (index 0-4): พยายามอัปเดต Metadata ถ้ายังเป็น None อยู่
                if i < 5:
                    page_meta = extract_project_metadata(text)
                    for key, value in page_meta.items():
                        # ถ้าของเดิมเป็น None แต่ของใหม่หาเจอ ให้แทนที่ด้วยของใหม่
                        if special_meta[key] is None and value is not None:
                            special_meta[key] = value

                # 4. ประกอบร่าง Data
                metadata = {
                    "source": os.path.basename(file_path),
                    "page_number": i + 1,
                    "total_pages": total_pages,
                    **special_meta  # Metadata ที่สกัดได้จะถูกฝังลงไปในทุกหน้า
                }

                extracted_data.append({
                    "content": text,
                    "metadata": metadata
                })
            
    return extracted_data