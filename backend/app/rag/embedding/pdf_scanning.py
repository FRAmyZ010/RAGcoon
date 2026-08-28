import os

import pdfplumber

from .metadata_extractor import extract_project_metadata


def scan_pdf_document(file_path):
    extracted_data = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        
        # 1. เตรียมตัวแปรเก็บ Metadata พิเศษ (ค่าเริ่มต้นเป็น None)
        special_meta: dict[str, str | None] = {
            "project_title": None, "author": None,
            "advisor": None, "committee": None, "keywords": None, "year": None
        }

        # 2. Collect metadata first so every page receives the final payload.
        page_texts = [
            page.extract_text(x_tolerance=1, y_tolerance=2) or ""
            for page in pdf.pages
        ]
        for text in page_texts[:5]:
            if text:
                page_meta = extract_project_metadata(text)
                for key, value in page_meta.items():
                    if special_meta[key] is None and value is not None:
                        special_meta[key] = value

        # 3. Loop through pages and attach the completed metadata payload.
        for i, text in enumerate(page_texts):

            if text:
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