"""
Module: extractor.py
Description:
    Dynamic Metadata Filter Extractor (Rule-based Fallback & Helper)
    - สกัดตัวกรองเมทาดาตาโดยอ้างอิงจาก Dynamic Metadata Cache ใน Qdrant 100%
    - ไม่มี Hardcode รายชื่ออาจารย์ ผู้จัดทำ หรือชื่อโครงงานในโค้ด
    - แปลงปี พ.ศ. (4 หลัก และ 2 หลัก) เป็นปี ค.ศ. แบบ Dynamic
"""

import re
from typing import Any

from .metadata_cache import metadata_cache, _NON_NAME_WORDS

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
THAI_BE_YEAR_PATTERN = re.compile(r"\b(25\d{2})\b")
THAI_SHORT_YEAR_PATTERN = re.compile(r"(?:ปี|พ\.ศ\.)\s*['\"]?([5-7]\d)\b")

KV_PATTERN = re.compile(
    r'(?:"?)\b(project_title|title|author|advisor|keywords?)\b(?:"?)\s*[:=]\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s"]+))',
    re.IGNORECASE,
)


def _extract_year(query: str) -> tuple[str | None, str]:
    """สกัดปีการศึกษา ทั้งปี ค.ศ., พ.ศ. 4 หลัก, และ พ.ศ. 2 หลัก (เช่น ปี 65 -> 2022)"""
    # 1. ค.ศ. (e.g. 2020, 2022, 2023)
    match_ce = YEAR_PATTERN.search(query)
    if match_ce:
        year_str = match_ce.group()
        clean_q = YEAR_PATTERN.sub("", query)
        return year_str, clean_q

    # 2. พ.ศ. 4 หลัก (e.g. 2565 -> 2022, 2563 -> 2020)
    match_be = THAI_BE_YEAR_PATTERN.search(query)
    if match_be:
        be_val = int(match_be.group())
        ce_val = str(be_val - 543)
        clean_q = THAI_BE_YEAR_PATTERN.sub("", query)
        return ce_val, clean_q

    # 3. พ.ศ. 2 หลัก (e.g. ปี 65 -> 2022, ปี 63 -> 2020)
    match_short = THAI_SHORT_YEAR_PATTERN.search(query)
    if match_short:
        short_val = int(match_short.group(1))
        be_val = 2500 + short_val
        ce_val = str(be_val - 543)
        clean_q = query[:match_short.start()] + " " + query[match_short.end():]
        return ce_val, clean_q

    return None, query


def _extract_advisor(query: str) -> tuple[str | None, str]:
    """สกัดชื่ออาจารย์ที่ปรึกษาแบบ Dynamic จาก Metadata Cache ใน Qdrant"""
    clean_q = query

    for advisor in sorted(metadata_cache.advisors, key=len, reverse=True):
        if len(advisor) > 3 and advisor.lower() in clean_q.lower():
            clean_q = re.sub(re.escape(advisor), "", clean_q, flags=re.IGNORECASE)
            return advisor, clean_q

        # จับคู่คำสำคัญของชื่ออาจารย์ (First Name / Last Name)
        for word in re.findall(r"[A-Za-z]+", advisor):
            if len(word) >= 4 and word.lower() not in {"prof", "asst", "assoc", "doctor", "lecturer", "dr", "aj"}:
                if re.search(rf"\b{re.escape(word)}\b", clean_q, re.IGNORECASE):
                    clean_q = re.sub(rf"\b{re.escape(word)}\b", "", clean_q, flags=re.IGNORECASE)
                    return advisor, clean_q

    return None, query


def _find_matching_project_title(query: str, titles: set[str]) -> tuple[str | None, str]:
    """สกัดชื่อโครงงานแบบ Dynamic จาก Metadata Cache ใน Qdrant"""
    clean_q = query

    for title in sorted(titles, key=len, reverse=True):
        if len(title) > 3 and title.lower() in clean_q.lower():
            clean_q = re.sub(re.escape(title), "", clean_q, flags=re.IGNORECASE)
            return title, clean_q

    return None, query


def _extract_authors(query: str) -> tuple[list[str], str]:
    """สกัดรายชื่อผู้จัดทำทั้งหมดแบบ Dynamic จาก Metadata Cache ใน Qdrant"""
    matched_authors: list[str] = []
    clean_q = query

    # 1. เช็คจากชื่อผู้จัดทำเต็มใน metadata_cache
    for author in sorted(metadata_cache.authors, key=len, reverse=True):
        if len(author) > 3 and author.lower() in clean_q.lower():
            if author not in matched_authors:
                matched_authors.append(author)
            clean_q = re.sub(re.escape(author), "", clean_q, flags=re.IGNORECASE)

    # 2. เช็คจากชื่อเดี่ยว (First name / Last name)
    for word in re.findall(r"[A-Za-z]+", clean_q):
        w_lower = word.lower()
        if len(w_lower) >= 4 and w_lower not in _NON_NAME_WORDS:
            for cand in sorted(metadata_cache.authors, key=len, reverse=True):
                words_in_cand = [cw.lower() for cw in cand.split()]
                if w_lower in words_in_cand:
                    if cand not in matched_authors:
                        matched_authors.append(cand)
                    clean_q = re.sub(re.escape(word), "", clean_q, flags=re.IGNORECASE)
                    break

    return matched_authors, clean_q


class QueryFilterProcessor:
    """ประมวลผลสกัด Filter และทำความสะอาดคำค้นหาอย่างสมบูรณ์แบบด้วย Dynamic Metadata"""

    def __init__(self, user_query: str):
        self.user_query = user_query

    def parse(self) -> tuple[str, dict[str, Any]]:
        metadata_cache.load_metadata()
        filters: dict[str, Any] = {}
        clean_q = self.user_query

        # 1. Key-Value Syntax (e.g. advisor: "Surapol", year: 2022, author: "Phumphol")
        for match in KV_PATTERN.finditer(self.user_query):
            k = match.group(1).lower()
            v = match.group(2) or match.group(3) or match.group(4)
            if v:
                if k in ("title", "project_title"):
                    filters["project_title"] = v.strip()
                elif k == "advisor":
                    adv_match, _ = _extract_advisor(v)
                    filters["advisor"] = adv_match or v.strip()
                elif k == "author":
                    auth_matches, _ = _extract_authors(v)
                    if auth_matches:
                        filters["author"] = auth_matches if len(auth_matches) > 1 else auth_matches[0]
                    else:
                        filters["author"] = v.strip()
                elif k == "year":
                    y_match, _ = _extract_year(v)
                    filters["year"] = y_match or v.strip()
                elif k in ("keyword", "keywords"):
                    pass
                clean_q = clean_q.replace(match.group(0), "")

        # 2. สกัดปีการศึกษา
        if "year" not in filters:
            year_val, clean_q = _extract_year(clean_q)
            if year_val:
                filters["year"] = year_val

        # 3. สกัดชื่ออาจารย์ที่ปรึกษา
        if "advisor" not in filters:
            adv_val, clean_q = _extract_advisor(clean_q)
            if adv_val:
                filters["advisor"] = adv_val

        # 4. สกัดชื่อผู้จัดทำ (Author / Multiple Authors)
        if "author" not in filters:
            auth_matches, clean_q = _extract_authors(clean_q)
            if auth_matches:
                filters["author"] = auth_matches if len(auth_matches) > 1 else auth_matches[0]

        # 5. สกัดชื่อโครงงาน (Project Title) - เฉพาะเมื่อไม่ได้เป็นคำถามภาพรวม
        is_broad = any(w in self.user_query.lower() for w in ["ไหนดี", "แนะนำ", "อะไรบ้าง", "which project", "recommend"])
        if "project_title" not in filters and not is_broad:
            title_val, clean_q = _find_matching_project_title(clean_q, metadata_cache.titles)
            if title_val:
                filters["project_title"] = title_val

        # 6. ล้างช่องว่างและปรับปรุงความหมายของ Clean Query
        clean_q = re.sub(r"[ \t]+", " ", clean_q).strip()

        if filters.get("project_title") and len(clean_q) < 8:
            clean_q = str(filters["project_title"])
        elif not clean_q or len(clean_q) <= 2:
            clean_q = self.user_query

        return clean_q, filters


def extract_query_and_filters(query: str) -> tuple[str, dict[str, Any]]:
    processor = QueryFilterProcessor(query)
    return processor.parse()
