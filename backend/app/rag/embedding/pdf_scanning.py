import os
import re
from typing import Any

import pdfplumber

from .category_registry import (
    categories_to_storage,
    normalize_categories,
    normalize_keywords,
    seed_categories,
)
from .enricher import extract_project_enrichment
from .metadata_extractor import extract_project_metadata


def _metadata_page_score(text: str) -> int:
    """Prefer the labelled Title/Author/Supervisory/Abstract metadata page."""
    score = 0
    if re.search(r"(?m)^\s*Title\b", text, re.IGNORECASE):
        score += 2
    if re.search(r"(?m)^\s*Author\b", text, re.IGNORECASE):
        score += 2
    if re.search(r"\bSupervisory\b", text, re.IGNORECASE):
        score += 2
    if re.search(r"\bAbstract\b", text, re.IGNORECASE) or "บทคัดย่อ" in text:
        score += 1
    return score


def scan_pdf_document(file_path, category_options: list[str] | None = None):
    extracted_data = []
    options = list(category_options or seed_categories())

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)

        # 1. เตรียมตัวแปรเก็บ Metadata พิเศษ
        special_meta: dict[str, Any] = {
            "project_title": None,
            "author": None,
            "advisor": None,
            "committee": None,
            "keywords": None,
            "year": None,
            "school": None,
            "program": None,
            "summary": None,
            "project_type": [],
            "key_technologies": [],
            "target_problem": None,
            "categories": ["Other"],
            "keyword_groups": "Other",
        }

        # 2. Collect metadata first so every page receives the final payload.
        # Prefer labelled metadata pages (Title + Supervisory + Abstract) over cover pages.
        file_basename = os.path.basename(file_path)
        page_texts = [
            page.extract_text(x_tolerance=1, y_tolerance=2) or ""
            for page in pdf.pages
        ]
        scored_pages: list[tuple[int, dict[str, Any]]] = []
        for text in page_texts[:5]:
            if not text:
                continue
            try:
                page_meta = extract_project_metadata(text, filename=file_basename)
            except TypeError:
                page_meta = extract_project_metadata(text)
            scored_pages.append((_metadata_page_score(text), page_meta))

        for _, page_meta in sorted(scored_pages, key=lambda item: -item[0]):
            for key, value in page_meta.items():
                if value is None:
                    continue
                current = special_meta.get(key)
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
                        has_label_leak = any(n.lower().startswith("author ") for n in current_names)
                        has_single_word_current = any(len(n.split()) == 1 for n in current_names)
                        all_multi_word_new = all(len(n.split()) >= 2 for n in new_names)
                        if has_label_leak or (has_single_word_current and all_multi_word_new):
                            special_meta[key] = value
                    elif key == "advisor":
                        # Prefer advisor that has academic title or is longer
                        if len(current) < 10 or (
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
                    elif key == "year":
                        if not re.search(r"\b(20[12]\d)\b", current) and re.search(r"\b(20[12]\d)\b", value):
                            special_meta[key] = value

        # 3. LLM: Abstract (+ existing Keyword line) → refined keywords + categories
        abstract_candidates = []
        for text in page_texts[:6]:
            if text and ("ABSTRACT" in text.upper() or "บทคัดย่อ" in text):
                abstract_candidates.append(text)
        enrichment_text = "\n\n".join(abstract_candidates) if abstract_candidates else "\n\n".join(page_texts[:4])
        existing_keywords = special_meta.get("keywords")

        enrichment = extract_project_enrichment(
            enrichment_text,
            project_title=special_meta.get("project_title"),
            existing_keywords=existing_keywords if isinstance(existing_keywords, str) else None,
            category_options=options,
        )
        special_meta["summary"] = enrichment.get("summary")
        special_meta["project_type"] = enrichment.get("project_type") or []
        special_meta["key_technologies"] = enrichment.get("key_technologies") or []
        special_meta["target_problem"] = enrichment.get("target_problem")

        refined_keywords = normalize_keywords(enrichment.get("keywords"))
        if not refined_keywords:
            refined_keywords = normalize_keywords(existing_keywords)
        if not refined_keywords:
            refined_keywords = normalize_keywords(special_meta.get("key_technologies"))
        special_meta["keywords"] = ", ".join(refined_keywords) if refined_keywords else None

        categories = normalize_categories(enrichment.get("categories"), options)
        special_meta["categories"] = categories
        special_meta["keyword_groups"] = categories_to_storage(categories)

        # 4. Keep every scanned page in order. Blank pages should still carry their
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