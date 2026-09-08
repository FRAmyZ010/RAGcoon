"""
Module: llm_query_processor.py
Description:
    ระบบวิเคราะห์และปรับแต่งคำถามด้วย LLM (Ollama-based Query Normalizer & Dynamic Filter Extractor)
    - โหลดรายชื่ออาจารย์ โครงงาน และปีการศึกษาจาก Qdrant Vector Database แบบ Dynamic อัตโนมัติ (รองรับไฟล์ใหม่ทันที)
    - แปลงคำถามภาษาธรรมชาติ / ภาษาพูด / คำสะกดผิด / ภาษาไทย ให้เป็น Academic Search Query ภาษาอังกฤษ
    - สกัดเงื่อนไขตัวกรอง (Metadata Filters: advisor, year, project_title, author, keywords) ในรูปแบบ JSON สำหรับใส่ใน Qdrant
    - มี Fallback ป้องกันกรณี Ollama ขัดข้องหรือไม่ตอบสนองภายใน Timeout
"""

import json
import os
import re
from typing import Any, Optional
import requests
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field

from .metadata_cache import metadata_cache

env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(find_dotenv(usecwd=True))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
LLM_TIMEOUT = int(os.getenv("LLM_QUERY_TIMEOUT", "60"))


class QueryFilterResult(BaseModel):
    normalized_query: str = Field(
        ...,
        description="Search query translated/expanded into technical English keywords, corrected for typos.",
    )
    advisor: Optional[str] = Field(None, description="Advisor name mapped to canonical repository list.")
    year: Optional[str] = Field(None, description="4-digit Christian Era year (e.g., 2020, 2022, 2023).")
    project_title: Optional[str] = Field(None, description="Exact project title if specifically queried.")
    author: Optional[Any] = Field(None, description="Author student name(s) (string or array of strings) if specifically queried.")
    keywords: Optional[str] = Field(None, description="Domain keywords (e.g., IoT, BLE, MySQL, Arduino).")
    intent: str = Field("FACTOID", description="Query intent: EXPLORATORY, DEEP_DIVE, COMPARISON, CODE, FACTOID")


def _detect_intent_by_rules(raw_query: str, project_title_present: bool = False) -> str:
    """Rule-based intent detection fallback."""
    q = raw_query.lower()
    if any(k in q for k in ["code", "source code", "sql", "select", "function", "คำสั่ง", "โค้ด", "ฟังก์ชัน", ".php", ".py", ".js", ".java"]):
        return "CODE"
    if any(k in q for k in ["similar", "คล้าย", "เหมือน", "จัดกลุ่ม", "grouping", "group"]):
        return "EXPLORATORY"
    if any(k in q for k in ["compare", "comparison", "เปรียบเทียบ", "เทียบ", "แตกต่าง", " vs ", "versus", "ไหนดีกว่า", "ดีที่สุด"]):
        return "COMPARISON"
    if any(k in q for k in ["อย่างละเอียด", "in detail", "deep dive", "ละเอียด", "สถาปัตยกรรม", "architecture", "methodology", "ขั้นตอนการทำงาน", "การทำงานของระบบ"]):
        return "DEEP_DIVE"
    if any(k in q for k in ["มีอะไรบ้าง", "ขอเอกสาร", "แนะนำ", "any project", "list", "survey", "further", "ต่อยอด", "บ้าง", "projects", "โครงงานไหน", "which project"]):
        return "EXPLORATORY"
    if project_title_present:
        return "DEEP_DIVE"
    return "FACTOID"


def _build_dynamic_system_prompt() -> str:
    """
    สร้าง System Prompt โดยดึงข้อมูลรายชื่ออาจารย์ รายชื่อผู้จัดทำ โครงงาน และปีการศึกษาจาก Qdrant แบบ Real-Time
    (ทำให้เมื่อมีไฟล์ PDF ใหม่ถูกเพิ่มเข้า Qdrant ระบบจะรู้จักทันทีโดยไม่ต้องแก้โค้ด)
    """
    metadata_cache.load_metadata()

    current_advisors = sorted(list(metadata_cache.advisors))
    current_authors = sorted(list(metadata_cache.authors))
    current_projects = sorted(list(metadata_cache.titles))
    current_years = sorted(list(metadata_cache.years))

    return f"""You are an expert AI Query Normalizer & Metadata Filter Extractor for a Computer Engineering Senior Project Document QA system.

Your task is to analyze the user's raw query (which may be in Thai, English, have typos, informal slang, or relative dates) and return a JSON object with:
1. "normalized_query": Search query translated into concise, technical English keywords for semantic vector search (e.g. translate Thai terms 'บลูทูธ' -> 'Bluetooth low energy BLE', 'เครือข่ายไร้สาย' -> 'wireless networks', 'นัดหมายอาจารย์' -> 'lecturer appointment', 'คนไข้' -> 'patient discharge', 'ประหยัดพลังงาน' -> 'energy saving'). All subject topics, tech domains, and search keywords belong here.
2. "advisor": Exact matching advisor from the KNOWN ADVISORS list. (Thai names/prefixes like 'อาจารย์สุรพล' / 'อ.สุรพล' / 'สุรพล' must be mapped to 'Aj. Surapol Vorapatratorn', 'อ.มาหะมะ' / 'มาหะมะ' -> 'Dr. Mahamah Sebakor', etc.). Return null if not mentioned.
3. "author": Exact matching author name(s) from the KNOWN AUTHORS list. If multiple authors are mentioned, return a list/array of author names (e.g. ["FANA YAHLEE", "ROMTHEERA WANG"]). If single author, return a string (e.g. "PHUMPHOL CHANRUNGSRICHAY"). If not mentioned, return null.
4. "year": 4-digit academic year in Christian Era (e.g. convert Thai year 2565 or 65 -> 2022, 2563 or 63 -> 2020). Return null if no year is specified.
5. "project_title": Exact project title from the KNOWN PROJECTS list if specifically referenced, otherwise null.
6. "intent": One of ["EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"].
   - "EXPLORATORY": Broad search, survey, recommendations, listing multiple projects, similarity clustering across repository (e.g. "มีโปรเจกต์ไหนบ้าง", "Which projects have similar objectives?", "Are there any projects that could be developed further?"). DO NOT lock project_title filter.
   - "DEEP_DIVE": In-depth analysis of a single named project (e.g. "อธิบายระบบ X อย่างละเอียด", "Architecture of project Y").
   - "COMPARISON": Direct pairwise comparison between 2 specific named projects (e.g. "เปรียบเทียบ A กับ B", "Compare X and Y").
   - "CODE": Asking for source code, SQL, functions.
   - "FACTOID": Direct factual/metadata lookup (e.g. "Who is advisor of X?", "What year was Y?").

CURRENT REPOSITORY METADATA IN QDRANT (DYNAMIC):
KNOWN ADVISORS:
{json.dumps(current_advisors, ensure_ascii=False, indent=2)}

KNOWN AUTHORS:
{json.dumps(current_authors, ensure_ascii=False, indent=2)}

KNOWN PROJECTS:
{json.dumps(current_projects, ensure_ascii=False, indent=2)}

KNOWN YEARS:
{json.dumps(current_years, ensure_ascii=False, indent=2)}

OUTPUT FORMAT (STRICT JSON ONLY, NO MARKDOWN, NO CODEBLOCKS):
{{
  "normalized_query": "English technical search keywords",
  "advisor": "Exact Advisor Name or null",
  "author": ["Author 1", "Author 2"] or "Exact Author Name" or null,
  "year": "2022 or null",
  "project_title": "Exact Title or null",
  "intent": "EXPLORATORY"
}}"""


def _call_ollama_for_query_parsing(raw_query: str) -> Optional[dict[str, Any]]:
    """เรียก Ollama Local API เพื่อประมวลผล Query"""
    system_prompt = _build_dynamic_system_prompt()
    user_prompt = f"User Query: \"{raw_query}\"\nJSON Output:"

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "format": "json",
            "keep_alive": "15m",
            "options": {
                "temperature": 0.0,
                "num_predict": 256,
            },
        }
        res = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=LLM_TIMEOUT,
        )
        if res.status_code == 200:
            raw_output = res.json().get("response", "")
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception:
        pass

    return None


def process_query_with_llm(raw_query: str) -> tuple[str, dict[str, Any], str]:
    """
    ฟังก์ชันหลักสำหรับเรียกใช้งาน:
    รับคำถามดิบของผู้ใช้ -> คืนค่า (clean_query_for_vector, filters_dict_for_qdrant, query_intent)
    """
    if not raw_query or not raw_query.strip():
        return "", {}, "FACTOID"

    from .extractor import QueryFilterProcessor
    from .normalizer import normalize_user_query

    # 1. เรียก Ollama วิเคราะห์คำถามแบบ Dynamic
    llm_result = _call_ollama_for_query_parsing(raw_query)

    if llm_result:
        norm_query = llm_result.get("normalized_query", "").strip() or raw_query
        filters: dict[str, Any] = {}
        intent = str(llm_result.get("intent", "")).upper().strip()

        if llm_result.get("advisor"):
            raw_advisor = str(llm_result["advisor"]).strip()
            matched_advisor = None
            for ca in metadata_cache.advisors:
                if raw_advisor.lower() == ca.lower() or raw_advisor.lower() in ca.lower():
                    matched_advisor = ca
                    break
            filters["advisor"] = matched_advisor or raw_advisor

        if llm_result.get("year"):
            filters["year"] = str(llm_result["year"]).strip()

        if llm_result.get("project_title"):
            filters["project_title"] = str(llm_result["project_title"]).strip()

        if llm_result.get("author"):
            raw_author = llm_result["author"]
            raw_authors_list = raw_author if isinstance(raw_author, list) else [raw_author]
            resolved_authors = []
            for item in raw_authors_list:
                for sub_item in str(item).split(","):
                    s = sub_item.strip()
                    if not s:
                        continue
                    matched = None
                    for ca in metadata_cache.authors:
                        if s.lower() == ca.lower():
                            matched = ca
                            break
                        elif s.lower() in ca.lower():
                            matched = ca
                    resolved_name = matched or s
                    if resolved_name not in resolved_authors:
                        resolved_authors.append(resolved_name)
            if resolved_authors:
                filters["author"] = resolved_authors if len(resolved_authors) > 1 else resolved_authors[0]

        if llm_result.get("keywords"):
            kw = str(llm_result["keywords"]).strip()
            if kw and kw.lower() not in norm_query.lower():
                norm_query = f"{norm_query} {kw}".strip()

        # Hybrid Enrichment: ถ้า LLM พลาด filter สำคัญ ให้ตัว extractor ดึงเสริม
        clean_norm = normalize_user_query(raw_query)
        processor = QueryFilterProcessor(clean_norm)
        _, rule_filters = processor.parse()
        for k, v in rule_filters.items():
            if k not in filters:
                filters[k] = v
            elif k == "author":
                current_authors = filters[k] if isinstance(filters[k], list) else [filters[k]]
                rule_authors = v if isinstance(v, list) else [v]
                merged = list(dict.fromkeys(current_authors + rule_authors))
                filters[k] = merged if len(merged) > 1 else merged[0]

        valid_intents = {"EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"}
        if intent not in valid_intents or any(w in raw_query.lower() for w in ["similar", "คล้าย", "เหมือน", "group", "กลุ่ม"]):
            intent = _detect_intent_by_rules(raw_query, project_title_present=bool(filters.get("project_title")))

        # Multi-project modes must not lock to a single project filter
        if intent in {"EXPLORATORY", "COMPARISON"}:
            filters.pop("project_title", None)

        return norm_query, filters, intent

    # 2. Fallback: กรณี Ollama ปิดอยู่หรือ Timeout ให้สลับไปใช้ In-Memory Cache อัตโนมัติ
    clean_norm = normalize_user_query(raw_query)
    processor = QueryFilterProcessor(clean_norm)
    clean_q, fallback_filters = processor.parse()
    fallback_intent = _detect_intent_by_rules(raw_query, project_title_present=bool(fallback_filters.get("project_title")))
    if fallback_intent in {"EXPLORATORY", "COMPARISON"}:
        fallback_filters.pop("project_title", None)
    return clean_q, fallback_filters, fallback_intent
