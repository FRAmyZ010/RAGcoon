import os
import re

import pdfplumber

from .metadata_extractor import extract_project_metadata


def scan_pdf_document(file_path):
    extracted_data = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)

        # 1. เตรียมตัวแปรเก็บ Metadata พิเศษ (ค่าเริ่มต้นเป็น None)
        special_meta: dict[str, str | None] = {
            "project_title": None,
            "author": None,
            "advisor": None,
            "committee": None,
            "keywords": None,
            "year": None,
            "school": None,
            "program": None,
        }

        # 2. Collect metadata first so every page receives the final payload.
        file_basename = os.path.basename(file_path)
        page_texts = [
            page.extract_text(x_tolerance=1, y_tolerance=2) or ""
            for page in pdf.pages
        ]
        for text in page_texts[:5]:
            if not text:
                continue
            try:
                page_meta = extract_project_metadata(text, filename=file_basename)
            except TypeError:
                page_meta = extract_project_metadata(text)
            for key, value in page_meta.items():
                if value is None:
                    continue
                current = special_meta[key]
                if current is None:
                    special_meta[key] = value
                else:
                    # Allow upgrading incomplete or truncated fields
                    if key == "project_title":
                        # Only upgrade title if current is None, or if current has "PROPOSAL" and new doesn't
                        if current is None or ("PROPOSAL" in current.upper() and "PROPOSAL" not in value.upper()):
                            special_meta[key] = value
                    elif key == "author":
                        current_names = [n.strip() for n in current.split(",") if n.strip()]
                        new_names = [n.strip() for n in value.split(",") if n.strip()]
                        has_single_word_current = any(len(n.split()) == 1 for n in current_names)
                        all_multi_word_new = all(len(n.split()) >= 2 for n in new_names)
                        if has_single_word_current and all_multi_word_new:
                            special_meta[key] = value
                    elif key == "advisor":
                        # Prefer advisor that has academic title or is longer
                        if len(current) < 5 or (
                            re.search(r"\b(?:Dr\.|Prof\.|Aj\.|Asst\.|Assoc\.)", value)
                            and not re.search(r"\b(?:Dr\.|Prof\.|Aj\.|Asst\.|Assoc\.)", current)
                        ):
                            special_meta[key] = value
                    elif key == "committee":
                        # Prefer committee lists with more members
                        current_count = len([c for c in current.split(",") if c.strip()])
                        new_count = len([c for c in value.split(",") if c.strip()])
                        if new_count > current_count:
                            special_meta[key] = value
                    elif key == "keywords":
                        if len(value) > len(current):
                            special_meta[key] = value
                    elif key == "year":
                        if not re.search(r"\b(20[12]\d)\b", current) and re.search(r"\b(20[12]\d)\b", value):
                            special_meta[key] = value

        # 3. Keep every scanned page in order. Blank pages should still carry their
        #    original page number so the numbering stays aligned with the PDF scan.
        for i, text in enumerate(page_texts):
            metadata = {
                "source": os.path.basename(file_path),
                "page_number": i + 1,
                "total_pages": total_pages,
                **special_meta,
            }

            extracted_data.append({
                "content": text,
                "metadata": metadata,
            })

    return extracted_data