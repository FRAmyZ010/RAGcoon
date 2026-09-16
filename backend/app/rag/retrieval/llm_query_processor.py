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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
LLM_TIMEOUT = int(os.getenv("LLM_QUERY_TIMEOUT", "60"))

# Persistent HTTP session for connection pooling & low latency
_http_session = requests.Session()
_cached_system_prompt: Optional[str] = None
_cached_meta_hash: int = 0


class QueryFilterResult(BaseModel):
    normalized_query: str = Field(
        ...,
        description="Search query translated into concise, technical English keywords for semantic vector search.",
    )
    advisor: Optional[str] = Field(None, description="Exact advisor name from known list if specifically queried.")
    year: Optional[str] = Field(None, description="4-digit Christian Era academic year if specifically queried.")
    project_title: Optional[str] = Field(None, description="Exact project title if specifically queried.")
    author: Optional[Any] = Field(None, description="Author student name(s) (string or array of strings) if specifically queried.")
    keywords: Optional[str] = Field(None, description="Domain keywords (e.g., IoT, BLE, MySQL, Arduino).")
    intent: str = Field("FACTOID", description="Query intent: RECOMMENDATION, EXPLORATORY, DEEP_DIVE, COMPARISON, CODE, FACTOID")


def _detect_intent_by_rules(raw_query: str, project_title_present: bool = False) -> str:
    """Rule-based intent detection fallback."""
    q = raw_query.lower()
    if any(k in q for k in ["code", "source code", "sql", "select", "function", "คำสั่ง", "โค้ด", "ฟังก์ชัน", ".php", ".py", ".js", ".java"]):
        return "CODE"
    if any(k in q for k in ["recommend", "recommendation", "suggest", "suggestion", "แนะนำ", "น่าสนใจ", "น่าทำ", "ต่อยอด", "future work", "further study", "ไอเดีย", "เลือกหัวข้อ"]):
        return "RECOMMENDATION"
    if any(k in q for k in ["similar", "คล้าย", "เหมือน", "จัดกลุ่ม", "grouping", "group"]):
        return "EXPLORATORY"
    if any(k in q for k in ["compare", "comparison", "เปรียบเทียบ", "เทียบ", "แตกต่าง", " vs ", "versus", "ไหนดีกว่า", "ดีที่สุด", "matrix", "แมทริกซ์", "ให้คะแนน", "ประเมิน", "evaluate", "scoring", "score"]):
        return "COMPARISON"
    if any(k in q for k in ["อย่างละเอียด", "in detail", "deep dive", "ละเอียด", "สถาปัตยกรรม", "architecture", "methodology", "ขั้นตอนการทำงาน", "การทำงานของระบบ"]):
        return "DEEP_DIVE"
    # Factual lookup about a single project's advisor/author/year/status
    if any(who_word in q for who_word in ["who", "ใคร", "ชื่ออะไร", "what is the advisor", "advisor of", "author of", "creator of"]):
        return "FACTOID"
    if any(adv_word in q for adv_word in ["advisor", "advised", "ที่ปรึกษา", "ดูแล"]) and any(proj_word in q for proj_word in ["project", "projects", "โครงงาน", "โปรเจกต์"]):
        if any(k in q for k in ["มีอะไรบ้าง", "อะไรบ้าง", "list", "which", "recommend", "แนะนำ", "บ้าง", "survey"]):
            return "EXPLORATORY"
        if not project_title_present and not any(w in q for w in ["นี้", "this", "it", "โปรเจกต์นี้"]):
            return "EXPLORATORY"
        return "FACTOID"
    if any(k in q for k in ["มีอะไรบ้าง", "ขอเอกสาร", "any project", "list", "survey", "further", "บ้าง", "projects", "โครงงานไหน", "which project"]):
        return "EXPLORATORY"
    if project_title_present:
        return "DEEP_DIVE"
    return "FACTOID"


def _build_dynamic_system_prompt() -> str:
    """
    สร้าง System Prompt โดยดึงข้อมูลรายชื่ออาจารย์ รายชื่อผู้จัดทำ โครงงาน และปีการศึกษาจาก Qdrant แบบ Real-Time
    (แคชผลลัพธ์ไว้เพื่อประสิทธิภาพสูงสุด และรีเฟรชเมื่อมีการเพิ่มเอกสารใหม่)
    """
    global _cached_system_prompt, _cached_meta_hash

    metadata_cache.load_metadata()

    current_meta_hash = hash((
        len(metadata_cache.advisors),
        len(metadata_cache.authors),
        len(metadata_cache.titles),
        len(metadata_cache.years),
    ))

    if _cached_system_prompt is not None and _cached_meta_hash == current_meta_hash:
        return _cached_system_prompt

    current_advisors = sorted(list(metadata_cache.advisors))
    current_authors = sorted(list(metadata_cache.authors))
    current_projects = sorted(list(metadata_cache.titles))
    current_years = sorted(list(metadata_cache.years))

    _cached_system_prompt = f"""You are an expert AI Query Normalizer & Metadata Filter Extractor for a Computer Engineering Senior Project Document QA system.

Your task is to analyze the user's raw query (which may be in Thai, English, have typos, informal slang, or relative dates) and return a JSON object with:
1. "normalized_query": Search query translated into concise, technical English keywords for semantic vector search (e.g. translate Thai terms 'บลูทูธ' -> 'Bluetooth low energy BLE', 'เครือข่ายไร้สาย' -> 'wireless networks', 'นัดหมายอาจารย์' -> 'lecturer appointment', 'คนไข้' -> 'patient discharge', 'ประหยัดพลังงาน' -> 'energy saving'). All subject topics, tech domains, and search keywords belong here.
2. "advisor": Exact matching advisor from the KNOWN ADVISORS list. (Thai names/prefixes like 'อาจารย์สุรพล' / 'อ.สุรพล' / 'สุรพล' must be mapped to 'Aj. Surapol Vorapatratorn', 'อ.มาหะมะ' / 'มาหะมะ' -> 'Dr. Mahamah Sebakor', etc.). Return null if asking WHO is the advisor or if not mentioned.
3. "author": Exact matching author name(s) from the KNOWN AUTHORS list. If multiple authors are mentioned, return a list/array of author names (e.g. ["FANA YAHLEE", "ROMTHEERA WANG"]). If single author, return a string (e.g. "PHUMPHOL CHANRUNGSRICHAY"). If not mentioned, return null.
4. "year": 4-digit academic year in Christian Era (e.g. convert Thai year 2565 or 65 -> 2022, 2563 or 63 -> 2020). Return null if no year is specified.
5. "project_title": Exact project title from the KNOWN PROJECTS list if specifically referenced, otherwise null.
6. "intent": One of ["RECOMMENDATION", "EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"].
   - "RECOMMENDATION": Asking for project recommendations, ideas, suggestions, interesting topics to study or build upon (e.g. "แนะนำโปรเจกต์หน่อย", "Could you recommend some projects?", "มีโปรเจกต์ไหนน่าสนใจเอาไปทำต่อยอดได้บ้าง", "Suggest some good projects"). DO NOT lock project_title filter.
   - "EXPLORATORY": Surveying, listing, or searching multiple projects in a specific domain or advised by a specific teacher (e.g. "มีโปรเจกต์เกี่ยวกับ IoT อะไรบ้าง", "อาจารย์สุรพล ดูแลโปรเจกต์อะไรบ้าง", "List all web projects"). DO NOT lock project_title filter.
   - "DEEP_DIVE": In-depth analysis of a single named project (e.g. "อธิบายระบบ X อย่างละเอียด", "Architecture of project Y").
   - "COMPARISON": Direct pairwise comparison between 2 specific named projects (e.g. "เปรียบเทียบ A กับ B", "Compare X and Y").
   - "CODE": Asking for source code, SQL, functions.
   - "FACTOID": Direct factual/metadata lookup (e.g. "Who is the advisor of X?", "ใครเป็นอาจารย์ที่ปรึกษาของโปรเจกต์นี้?", "What year was Y?", "Who created Z?").

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
    _cached_meta_hash = current_meta_hash
    return _cached_system_prompt


def _call_ollama_for_query_parsing(raw_query: str, chat_history: Optional[str] = None) -> Optional[dict[str, Any]]:
    """เรียก Ollama Local API เพื่อประมวลผล Query โดยนำบริบทสนทนาก่อนหน้า (chat_history) มาร่วมวิเคราะห์"""
    system_prompt = _build_dynamic_system_prompt()
    if chat_history and chat_history.strip():
        user_prompt = f"Recent Conversation History:\n{chat_history.strip()}\n\nCurrent User Query: \"{raw_query}\"\n(Note: Resolve any pronouns like 'โปรเจกต์นี้', 'เขา', 'it', 'this project', 'his/her' using the recent conversation history to find the referenced project/advisor/year)\nJSON Output:"
    else:
        user_prompt = f"User Query: \"{raw_query}\"\nJSON Output:"

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "options": {
                "temperature": 0.0,
                "num_predict": 128,
            },
        }
        res = _http_session.post(
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

def _fast_path_check(raw_query: str) -> Optional[tuple[str, dict[str, Any], str]]:
    """
    Fast-Path Shortcut:
    ตรวจจับคำถามที่มีชื่อโปรเจกต์ หรือชื่ออาจารย์ที่ปรึกษาชัดเจน เพื่อข้ามการเรียก LLM
    ช่วยลดเวลา Query Processing จาก ~8s เหลือ ~0.001s ทันที
    """
    if not raw_query or not raw_query.strip():
        return None

    metadata_cache.load_metadata()
    q_clean = raw_query.strip()
    q_lower = q_clean.lower()

    # 1. ค้นหาชื่อโครงงานทั้งหมดที่ตรงกับ Metadata
    matched_titles = []
    for title in metadata_cache.titles:
        t_low = title.lower()
        if t_low in q_lower or (len(t_low) > 8 and t_low[:18] in q_lower):
            if title not in matched_titles:
                matched_titles.append(title)

    # 2. ค้นหาชื่ออาจารย์ที่ปรึกษา (รองรับชื่อเล่น/คำนำหน้าภาษาไทย)
    matched_advisor = None
    advisor_aliases = {
        "สุรพล": "Aj. Surapol Vorapatratorn",
        "surapol": "Aj. Surapol Vorapatratorn",
        "มาหะมะ": "Aj. Dr.Mahamah Sebakor",
        "mahamah": "Aj. Dr.Mahamah Sebakor",
        "ทศพร": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
        "tossapon": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
        "ณัฐพล": "Assoc.Prof. Nattapol Aunsri, Ph.D",
        "nattapol": "Assoc.Prof. Nattapol Aunsri, Ph.D",
        "ภัทรมน": "Asst. Prof. Pattaramon Vuttipittayamongkol, Ph.D",
        "pattaramon": "Asst. Prof. Pattaramon Vuttipittayamongkol, Ph.D",
    }
    for alias, canonical in advisor_aliases.items():
        if alias in q_lower:
            matched_advisor = canonical
            break
    if not matched_advisor:
        for adv in metadata_cache.advisors:
            if adv.lower() in q_lower:
                matched_advisor = adv
                break

    # 3. Intent Detection
    intent = _detect_intent_by_rules(raw_query, project_title_present=bool(matched_titles))

    # Fast-path case 1: เปรียบเทียบหลายโครงงาน (COMPARISON)
    if intent == "COMPARISON":
        if len(matched_titles) >= 2:
            norm_q = " vs ".join(matched_titles)
            return norm_q, {}, intent
        # ถ้าจับคู่ได้แค่ 1 ชื่อในโหมดเปรียบเทียบ ให้ส่งต่อ LLM ช่วยแยกแยะ
        return None

    # Fast-path case 2: เจาะจงโครงงานเดี่ยว
    if len(matched_titles) == 1:
        matched_title = matched_titles[0]
        filters: dict[str, Any] = {}
        if intent not in {"EXPLORATORY", "COMPARISON"}:
            filters["project_title"] = matched_title
        if matched_advisor:
            filters["advisor"] = matched_advisor
        return matched_title, filters, intent

    # Fast-path case 2: ค้นหาโครงงานตามอาจารย์ที่ปรึกษา
    if matched_advisor and any(k in q_lower for k in ["โปรเจกต์", "project", "โครงงาน", "ที่ปรึกษา", "ดูแล", "มีอะไรบ้าง", "ใคร"]):
        filters = {"advisor": matched_advisor}
        norm_q = f"senior projects advised by {matched_advisor}"
        return norm_q, filters, "EXPLORATORY"

    return None


def process_query_with_llm(raw_query: str, chat_history: Optional[str] = None) -> tuple[str, dict[str, Any], str]:
    """
    ฟังก์ชันหลักสำหรับเรียกใช้งาน:
    รับคำถามดิบของผู้ใช้ -> คืนค่า (clean_query_for_vector, filters_dict_for_qdrant, query_intent)
    """
    if not raw_query or not raw_query.strip():
        return "", {}, "FACTOID"

    from .extractor import QueryFilterProcessor
    from .normalizer import normalize_user_query

    # 0. Fast-Path Shortcut check (ประหยัดเวลา ~8 วินาทีเมื่อเจอ Pattern ชัดเจน)
    fast_result = _fast_path_check(raw_query)
    if fast_result:
        return fast_result

    # 1. เรียก Ollama วิเคราะห์คำถามแบบ Dynamic
    llm_result = _call_ollama_for_query_parsing(raw_query, chat_history=chat_history)

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
            raw_title = str(llm_result["project_title"]).strip()
            matched_title = None
            for ct in metadata_cache.titles:
                if raw_title.lower() == ct.lower():
                    matched_title = ct
                    break
                if ct.lower() in raw_title.lower() or raw_title.lower() in ct.lower():
                    matched_title = ct
                    break
                if len(ct) > 10 and len(raw_title) > 10 and (ct.lower()[:20] == raw_title.lower()[:20]):
                    matched_title = ct
                    break
            filters["project_title"] = matched_title or raw_title

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

        valid_intents = {"RECOMMENDATION", "EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"}
        if intent not in valid_intents or any(w in raw_query.lower() for w in ["similar", "คล้าย", "เหมือน", "group", "กลุ่ม"]):
            intent = _detect_intent_by_rules(raw_query, project_title_present=bool(filters.get("project_title")))

        if filters.get("advisor") and any(w in raw_query.lower() for w in ["projects", "โครงงาน", "โปรเจกต์", "งาน", "มีอะไรบ้าง", "list", "บ้าง"]) and not any(w in raw_query.lower() for w in ["who", "ใคร", "recommend", "แนะนำ"]) and not filters.get("project_title"):
            intent = "EXPLORATORY"

        # Multi-project modes must not lock to a single project filter
        if intent in {"RECOMMENDATION", "EXPLORATORY", "COMPARISON"}:
            filters.pop("project_title", None)

        return norm_query, filters, intent

    # 2. Fallback: กรณี Ollama ปิดอยู่หรือ Timeout ให้สลับไปใช้ In-Memory Cache อัตโนมัติ
    clean_norm = normalize_user_query(raw_query)
    processor = QueryFilterProcessor(clean_norm)
    clean_q, fallback_filters = processor.parse()
    fallback_intent = _detect_intent_by_rules(raw_query, project_title_present=bool(fallback_filters.get("project_title")))
    if fallback_filters.get("advisor") and any(w in raw_query.lower() for w in ["projects", "โครงงาน", "โปรเจกต์", "งาน", "มีอะไรบ้าง", "list", "บ้าง"]) and not any(w in raw_query.lower() for w in ["who", "ใคร", "recommend", "แนะนำ"]) and not fallback_filters.get("project_title"):
        fallback_intent = "EXPLORATORY"
    if fallback_intent in {"RECOMMENDATION", "EXPLORATORY", "COMPARISON"}:
        fallback_filters.pop("project_title", None)
    return clean_q, fallback_filters, fallback_intent
