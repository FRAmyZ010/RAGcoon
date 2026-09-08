"""
Module: normalizer.py
Description:
    Fast, lightweight text normalizer for basic query sanitization.
    (ตัด SymSpell dictionary และการดึง Qdrant ช้าๆ ออกทั้งหมดเพื่อเพิ่มความเร็วในการประมวลผล)
"""

import re
import unicodedata


def normalize_user_query(query: str) -> str:
    """
    Lightweight, deterministic query normalization:
    - Unicode NFKC normalization (แก้ตัวอักษรควบและฟอนต์พิเศษ)
    - ตัดช่องว่างและอักขระแฝงที่มองไม่เห็น
    - รวดเร็วระดับ Microsecond (0.0001s)
    """
    if not query:
        return ""

    # 1. Unicode NFKC Normalization
    text = unicodedata.normalize("NFKC", query)

    # 2. Clean invisible zero-width characters and control characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0\u202f\u2007]", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 3. Collapse multiple whitespace
    text = " ".join(text.strip().split())

    return text
