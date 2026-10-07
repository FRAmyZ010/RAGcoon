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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
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
    # 1. COMPARISON has highest priority (e.g. compare, comparison, เปรียบเทียบ, vs, versus, between ... and)
    if any(k in q for k in ["compare", "comparison", "เปรียบเทียบ", "เทียบ", "แตกต่าง", " vs ", "versus", "ไหนดีกว่า", "ดีที่สุด", "matrix", "แมทริกซ์", "ให้คะแนน", "ประเมิน", "evaluate", "scoring", "score", "between"]):
        return "COMPARISON"
    if any(k in q for k in ["code", "source code", "sql", "select", "function", "คำสั่ง", "โค้ด", "ฟังก์ชัน", ".php", ".py", ".js", ".java"]):
        return "CODE"
    recommend_triggers = [
        "recommend", "recommendation", "suggest", "suggestion",
        "แนะนำ", "น่าสนใจ", "น่าทำ", "ต่อยอด", "ทำต่อ", "พัฒนาต่อ",
        "future work", "further study", "further work", "further research",
        "further develop", "further development", "develop further", "developing further",
        "worth developing", "worth doing", "worth pursuing", "worth",
        "build upon", "building upon",
        "ไอเดีย", "เลือกหัวข้อ", "หัวข้อน่าสนใจ", "project idea", "project ideas",
        "topic idea", "topic ideas", "senior project idea", "senior project ideas",
        "good project to", "good topic", "suitable for",
    ]
    if any(k in q for k in recommend_triggers):
        return "RECOMMENDATION"
    if any(k in q for k in ["similar", "คล้าย", "เหมือน", "จัดกลุ่ม", "grouping", "group"]):
        return "EXPLORATORY"
    if any(k in q for k in [
        "summary", "summarize", "overview", "สรุป", "ภาพรวม", "อย่างละเอียด",
        "in detail", "deep dive", "ละเอียด", "สถาปัตยกรรม", "architecture",
        "methodology", "ขั้นตอนการทำงาน", "การทำงาน", "ทำงานอย่างไร", "อธิบาย",
        "explain", "describe", "how does", "how it works", "การทำงานของระบบ"
    ]):
        return "DEEP_DIVE"
    # Listing and exploratory queries across groups / years / advisors
    if any(k in q for k in [
        "ขอรายชื่อ", "รายชื่อ", "ทั้งหมด", "ทุกโครงงาน", "ทุกโปรเจกต์", "list all", "all projects",
        "show all", "list", "survey", "มีอะไรบ้าง", "อะไรบ้าง", "มีโครงงานอะไร", "โครงงานทั้งหมด",
        "โปรเจกต์ทั้งหมด", "โครงงานในปี", "โปรเจกต์ในปี", "which project", "ขอเอกสาร"
    ]):
        return "EXPLORATORY"
    # Specific factual questions about a project (microcontroller, sensor, tool, author, advisor, year, objective, etc.)
    if any(k in q for k in ["what", "who", "when", "which", "how many", "ใคร", "อะไร", "ปีไหน", "เมื่อไหร่", "sensor", "sensors", "microcontroller", "hardware", "tool", "tools", "database", "author", "advisor", "objective"]):
        return "FACTOID"
    if any(adv_word in q for adv_word in ["advisor", "advised", "ที่ปรึกษา", "ดูแล"]) and any(proj_word in q for proj_word in ["project", "projects", "โครงงาน", "โปรเจกต์"]):
        if not project_title_present and not any(w in q for w in ["นี้", "this", "it", "โปรเจกต์นี้"]):
            return "EXPLORATORY"
        return "FACTOID"
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
2. "advisor": Exact matching advisor from the KNOWN ADVISORS list. (Thai names/prefixes like 'อาจารย์สุรพล' / 'อ.สุรพล' / 'สุรพล' must be mapped to 'Aj. Surapol Vorapatratorn', 'อ.มาหะมะ' / 'มาหะมะ' -> 'Dr. Mahamah Sebakor', etc.). Return null if asking WHO is the advisor or if not mentioned in the CURRENT query.
3. "author": Exact matching author name(s) from the KNOWN AUTHORS list. If multiple authors are mentioned, return a list/array of author names (e.g. ["FANA YAHLEE", "ROMTHEERA WANG"]). If single author, return a string (e.g. "PHUMPHOL CHANRUNGSRICHAY"). If not mentioned in the CURRENT query, return null.
4. "year": 4-digit academic year in Christian Era (e.g. convert Thai year 2565 or 65 -> 2022, 2563 or 63 -> 2020). Return null if no year is specified in the CURRENT query.
5. "project_title": Exact project title from the KNOWN PROJECTS list if specifically referenced, otherwise null.
6. "intent": One of ["RECOMMENDATION", "EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"].
   - "RECOMMENDATION": Asking for project recommendations, ideas, suggestions, interesting topics to study, build upon, or develop further (e.g. "แนะนำโปรเจกต์หน่อย", "Could you recommend some projects?", "Are there any projects worth developing further into a mobile app?", "มีโปรเจกต์ไหนน่าสนใจเอาไปทำต่อยอดได้บ้าง"). DO NOT lock project_title or year filters.
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
  "advisor": null,
  "author": null,
  "year": null,
  "project_title": null,
  "intent": "FACTOID"
}}

IMPORTANT:
- Leave advisor, author, year, project_title as null unless explicitly stated in the CURRENT user query.
- Never invent or assume a year, advisor, author, or project title.
- If asking for ideas, suggestions, or projects to develop further/build upon, intent MUST be "RECOMMENDATION".
"""
    _cached_meta_hash = current_meta_hash
    return _cached_system_prompt


def _call_ollama_for_query_parsing(raw_query: str, chat_history: Optional[str] = None) -> Optional[dict[str, Any]]:
    """เรียก Ollama Local API เพื่อประมวลผล Query โดยนำบริบทสนทนาก่อนหน้า (chat_history) มาร่วมวิเคราะห์"""
    system_prompt = _build_dynamic_system_prompt()
    if chat_history and chat_history.strip():
        user_prompt = f"Recent Conversation History:\n{chat_history.strip()}\n\nCurrent User Query: \"{raw_query}\"\n(Note: Resolve explicit pronouns like 'โปรเจกต์นี้', 'this project', 'it' ONLY when the user explicitly refers to the previous entity. If the current query does not explicitly specify a filter or is a new/domain question, leave that filter null and do NOT inherit filters from previous turns.)\nJSON Output:"
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

def _extract_last_referenced_project(chat_history: Optional[str]) -> Optional[str]:
    """Find the most recently discussed project title from the conversation history."""
    if not chat_history or not chat_history.strip():
        return None
    metadata_cache.load_metadata()
    history_lower = chat_history.lower()
    last_pos = -1
    last_title = None
    for title in metadata_cache.titles:
        pos = history_lower.rfind(title.lower())
        if pos > last_pos:
            last_pos = pos
            last_title = title
    return last_title


def _fast_path_check(raw_query: str, chat_history: Optional[str] = None) -> Optional[tuple[str, dict[str, Any], str]]:
    """
    Fast-Path Shortcut:
    ตรวจจับคำถามที่มีชื่อโปรเจกต์, ปีการศึกษา, หรือชื่ออาจารย์ที่ปรึกษาชัดเจน หรือคำถามต่อเนื่อง (Follow-up) จาก Chat History
    ช่วยลดเวลา Query Processing จาก ~8s เหลือ ~0.001s ทันที
    """
    if not raw_query or not raw_query.strip():
        return None

    metadata_cache.load_metadata()
    q_clean = raw_query.strip()
    q_lower = q_clean.lower()

    # 1. สกัดปีการศึกษา (2020, 2563, ปี 63, etc.)
    from .extractor import _extract_year
    matched_year, _ = _extract_year(raw_query)

    # 2. ค้นหาชื่อโครงงานทั้งหมดที่ตรงกับ Metadata
    matched_titles = []
    # First pass: Direct full title or prefix match
    for title in sorted(metadata_cache.titles, key=len, reverse=True):
        t_low = title.lower()
        if t_low in q_lower or (len(t_low) > 8 and t_low[:18] in q_lower):
            if title not in matched_titles:
                matched_titles.append(title)

    # Second pass: Only if NO direct match was found, try multi-word phrase matching
    if not matched_titles:
        for title in sorted(metadata_cache.titles, key=len, reverse=True):
            t_low = title.lower()
            words = [w for w in re.split(r"[\s\-_]+", t_low) if len(w) >= 3 and w not in ["the", "and", "for", "system", "systems", "project", "proposal", "using", "with", "based", "application", "web"]]
            for i in range(len(words)):
                phrase = " ".join(words[i:i+2])
                if len(phrase) >= 8 and phrase in q_lower:
                    if title not in matched_titles:
                        matched_titles.append(title)
                    break

    # 2.1 ดึงโปรเจกต์ล่าสุดจาก Chat History เฉพาะเมื่อผู้ใช้ระบุคำสรรพนามชี้เฉพาะ (Explicit Pronouns) ถึงโปรเจกต์ก่อนหน้าเท่านั้น
    if not matched_titles and chat_history and chat_history.strip():
        explicit_follow_up_markers = [
            "the project", "this project", "this system", "that project", "about it", "of it",
            "โปรเจกต์นี้", "โครงงานนี้", "ระบบนี้", "เรื่องนี้", "โครงการนี้",
        ]
        # Never inherit when asking a generic recommendation or multi-project exploratory query
        is_generic_query = any(k in q_lower for k in [
            "recommend", "แนะนำ", "similar", "คล้าย", "list", "รายชื่อ", "ทั้งหมด",
            "all projects", "กี่โครงงาน", "กี่โปรเจกต์", "how many", "มีอะไรบ้าง", "อะไรบ้าง"
        ])
        if any(marker in q_lower for marker in explicit_follow_up_markers) and not is_generic_query:
            last_proj = _extract_last_referenced_project(chat_history)
            if last_proj:
                matched_titles = [last_proj]

    # 3. ค้นหาชื่ออาจารย์ที่ปรึกษา (รองรับชื่อเล่น/คำนำหน้าภาษาไทย)
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

    # 4. Intent Detection
    intent = _detect_intent_by_rules(raw_query, project_title_present=bool(matched_titles))

    # Fast-path case 1: เปรียบเทียบหลายโครงงาน (COMPARISON)
    if intent == "COMPARISON":
        if len(matched_titles) >= 2:
            norm_q = " vs ".join(matched_titles)
            return norm_q, {"compared_projects": matched_titles}, intent
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
        if matched_year:
            filters["year"] = matched_year
        # Extract remaining question keywords to keep search specific to the question asked
        clean_keywords = q_clean
        for t in matched_titles:
            clean_keywords = re.sub(re.escape(t), "", clean_keywords, flags=re.IGNORECASE).strip()
        norm_q = f"{matched_title} {clean_keywords}".strip() if clean_keywords else matched_title
        return norm_q, filters, intent

    # Fast-path case 3: Hybrid Filtering (Advisor + Year + Topic Keywords, or Advisor + Year)
    if matched_advisor and matched_year:
        filters = {"advisor": matched_advisor, "year": matched_year}
        clean_keywords = q_clean
        for alias in list(advisor_aliases.keys()) + [matched_advisor, matched_year]:
            clean_keywords = re.sub(rf"\b{re.escape(str(alias))}\b", "", clean_keywords, flags=re.IGNORECASE).strip()
        # Clean common Thai noise words
        clean_keywords = re.sub(r"มีโครงงานเกี่ยวกับ|ที่มีอาจารย์|เป็นที่ปรึกษา|ในปี|บ้างไหม|อาจารย์|ที่ปรึกษา|โครงงาน|โปรเจกต์|จัดทำ|เกี่ยวกับ", "", clean_keywords).strip()
        norm_q = f"{clean_keywords} {matched_advisor}".strip() if clean_keywords else f"senior projects advised by {matched_advisor} in {matched_year}"
        return norm_q, filters, intent

    # Fast-path case 4: ค้นหาโครงงานตามปีการศึกษา (Group / Exploratory by Year)
    is_explicit_year_list_or_count = any(k in q_lower for k in [
        "list all", "all projects", "show all", "list", "survey",
        "รายชื่อ", "ขอรายชื่อ", "ทั้งหมด", "ทุกโครงงาน", "ทุกโปรเจกต์",
        "มีอะไรบ้าง", "อะไรบ้าง", "มีกี่", "กี่โครงงาน", "กี่โปรเจกต์",
        "how many", "count", "number of", "total",
    ]) or bool(re.search(r"^(?:senior\s+)?projects\s+in\s+\d{4}\??$", q_lower.strip()))
    q_content_check = q_lower.replace("มีอะไรบ้าง", "").replace("อะไรบ้าง", "").replace("มีอะไร", "")
    is_content_query = any(k in q_content_check for k in [
        "what", "which", "how", "why", "who", "gpu", "cpu", "model", "train", "sensor",
        "hardware", "technology", "algorithm", "dataset", "accuracy", "คืออะไร", "ใช้อะไร", "รุ่นไหน",
    ])
    if matched_year and is_explicit_year_list_or_count and not is_content_query:
        if intent not in {"RECOMMENDATION", "COMPARISON", "DEEP_DIVE", "CODE"}:
            from .template_responder import _has_technical_keywords
            if not _has_technical_keywords(raw_query):
                filters = {"year": matched_year}
                norm_q = f"senior projects in academic year {matched_year}"
                return norm_q, filters, "EXPLORATORY"

    # Fast-path case 5: ค้นหาโครงงานตามอาจารย์ที่ปรึกษา
    q_adv_content_check = q_lower.replace("มีอะไรบ้าง", "").replace("อะไรบ้าง", "").replace("มีอะไร", "")
    is_advisor_content_query = any(k in q_adv_content_check for k in [
        "what", "which", "how", "why", "gpu", "cpu", "sensor", "hardware", "technology", "algorithm", "คืออะไร", "ใช้อะไร", "อย่างไร",
    ])
    if matched_advisor and any(k in q_lower for k in ["โปรเจกต์", "project", "โครงงาน", "ที่ปรึกษา", "ดูแล", "มีอะไรบ้าง", "ใคร", "รายชื่อ", "ทั้งหมด"]) and not is_advisor_content_query:
        if intent not in {"RECOMMENDATION", "COMPARISON", "DEEP_DIVE", "CODE"}:
            from .template_responder import _has_technical_keywords
            if not _has_technical_keywords(raw_query):
                filters = {"advisor": matched_advisor}
                norm_q = f"senior projects advised by {matched_advisor}"
                return norm_q, filters, "EXPLORATORY"

    # Fast-path case 6: นิยามคำศัพท์เทคนิคสั้นๆ หรือตัวย่อ ("X คืออะไร", "what is X", "X หมายถึงอะไร")
    def_match = re.search(r"^([a-zA-Z0-9\-\.\s]{2,25})\s*(?:คืออะไร|หมายถึงอะไร|คืออะไรครับ|คืออะไรคะ)\??$", q_clean, re.IGNORECASE)
    if not def_match:
        def_match = re.search(r"^(?:what is|what's|what are)\s+([a-zA-Z0-9\-\.\s]{2,25})\??$", q_clean, re.IGNORECASE)
    if def_match and not matched_titles and not matched_advisor:
        term = def_match.group(1).strip()
        if len(term.split()) <= 3:
            return term, {}, "FACTOID"

    # Fast-path case 7: ค้นหาโครงงานตามประเภทของระบบ / Domain (IoT, Web, Network, AI, Mobile, Cybersecurity)
    domain_map = {
        "machine learning": "AI & Machine Learning",
        "deep learning": "AI & Machine Learning",
        "ปัญญาประดิษฐ์": "AI & Machine Learning",
        "cybersecurity": "Cybersecurity",
        "ความปลอดภัย": "Cybersecurity",
        "mobile application": "Mobile Application",
        "mobile app": "Mobile Application",
        "แอปพลิเคชันมือถือ": "Mobile Application",
        "แอปมือถือ": "Mobile Application",
        "network & wireless": "Network & Wireless",
        "wireless communication": "Network & Wireless",
        "wireless lan": "Network & Wireless",
        "wireless": "Network & Wireless",
        "เน็ตเวิร์ก": "Network & Wireless",
        "เครือข่าย": "Network & Wireless",
        "network": "Network & Wireless",
        "hardware": "IoT & Hardware",
        "ฮาร์ดแวร์": "IoT & Hardware",
        "embedded": "IoT & Hardware",
        "robotics": "IoT & Hardware",
        "หุ่นยนต์": "IoT & Hardware",
        "iot": "IoT & Hardware",
        "ไอโอที": "IoT & Hardware",
        "web application": "Web Application",
        "web app": "Web Application",
        "website": "Web Application",
        "เว็บ": "Web Application",
        "web": "Web Application",
        "mobile": "Mobile Application",
        "โมบาย": "Mobile Application",
        "ai": "AI & Machine Learning",
        "security": "Cybersecurity",
    }
    if not matched_titles:
        is_domain_query = any(k in q_lower for k in [
            "โครงงาน", "โปรเจกต์", "project", "projects", "ระบบ", "มีอะไรบ้าง", "อะไรบ้าง",
            "มีเรื่องไหนบ้าง", "บ้างไหม", "list", "show", "มีกี่", "กี่โครงงาน", "กี่เรื่อง",
            "สาย", "ด้าน", "แนว", "ประเภท", "หมวด"
        ])
        if is_domain_query:
            matched_domain = None
            for d_kw, d_canon in domain_map.items():
                pattern = rf"(?:\b|(?<=[\s\u0E00-\u0E7F])){re.escape(d_kw)}(?:\b|(?=[\s\u0E00-\u0E7F]))"
                if re.search(pattern, q_lower):
                    matched_domain = d_canon
                    break
            if matched_domain:
                from .template_responder import _has_technical_keywords
                if not _has_technical_keywords(raw_query):
                    domain_filters: dict[str, Any] = {"project_type": matched_domain}
                    if matched_year:
                        domain_filters["year"] = matched_year
                    if matched_advisor:
                        domain_filters["advisor"] = matched_advisor
                    norm_q = f"senior projects in {matched_domain}"
                    return norm_q, domain_filters, "EXPLORATORY"

    return None



def _clean_filter_value(val: Any) -> Optional[str]:
    """Return cleaned string or None if falsy / null-like."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in {"null", "none", "nil", "n/a", "undefined", '""', "''"}:
        return None
    return s


def _is_year_explicitly_in_query(query: str, candidate_year: str) -> bool:
    """Check whether candidate_year is explicitly present or referenced in query."""
    if not candidate_year or not query:
        return False
    clean_cand = str(candidate_year).strip()
    q_low = query.lower()
    if clean_cand in q_low:
        return True
    try:
        ce_int = int(clean_cand)
        be_str = str(ce_int + 543)
        if be_str in q_low:
            return True
        short_be = be_str[-2:]
        if re.search(rf"(?:ปี|พ\.ศ\.)\s*['\"]?{short_be}\b", q_low):
            return True
    except (ValueError, TypeError):
        pass
    from .extractor import _extract_year
    extracted, _ = _extract_year(query)
    if extracted and extracted == clean_cand:
        return True
    if any(rel in q_low for rel in ["ปีล่าสุด", "ปีที่แล้ว", "latest year", "last year", "most recent year"]):
        return True
    return False


def _is_advisor_explicitly_in_query(query: str, candidate_advisor: str, chat_history: Optional[str] = None) -> bool:
    """Check whether candidate_advisor is explicitly mentioned in query or follow-up pronoun."""
    if not candidate_advisor or not query:
        return False
    q_low = query.lower()
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
    for alias, canon in advisor_aliases.items():
        if canon.lower() == candidate_advisor.lower() and alias in q_low:
            return True
    name_tokens = [
        w for w in re.findall(r"[a-z]+", candidate_advisor.lower())
        if len(w) >= 3 and w not in {"prof", "asst", "assoc", "doctor", "lecturer", "dr", "aj", "phd", "wg", "cdr"}
    ]
    if any(tok in q_low for tok in name_tokens):
        return True
    if chat_history and any(p in q_low for p in ["his project", "his projects", "her project", "her projects", "ของเขา", "ของท่าน", "อาจารย์ท่านนี้"]):
        if candidate_advisor.lower() in chat_history.lower():
            return True
    return False


def _is_title_explicitly_in_query(query: str, candidate_title: str, chat_history: Optional[str] = None) -> bool:
    """Check whether candidate_title is explicitly mentioned in query or follow-up pronoun."""
    if not candidate_title or not query:
        return False
    q_low = query.lower()
    t_low = candidate_title.lower()
    if t_low in q_low or (len(t_low) > 8 and t_low[:18] in q_low):
        return True
    words = [w for w in re.split(r"[\s\-_]+", t_low) if len(w) >= 3 and w not in ["the", "and", "for", "system", "systems", "project", "proposal", "using", "with", "based", "application", "web"]]
    for i in range(len(words)):
        phrase = " ".join(words[i:i+2])
        if len(phrase) >= 8 and phrase in q_low:
            return True
    if chat_history and any(p in q_low for p in ["the project", "this project", "this system", "that project", "โปรเจกต์นี้", "โครงงานนี้", "ระบบนี้"]):
        if candidate_title.lower() in chat_history.lower():
            return True
    return False


def _is_author_explicitly_in_query(query: str, candidate_author: str) -> bool:
    """Check whether candidate_author name tokens are in query."""
    if not candidate_author or not query:
        return False
    q_low = query.lower()
    name_tokens = [w for w in re.findall(r"[a-z]+", candidate_author.lower()) if len(w) >= 3 and w not in _NON_NAME_WORDS]
    return any(tok in q_low for tok in name_tokens)


def process_query_with_llm(raw_query: str, chat_history: Optional[str] = None) -> tuple[str, dict[str, Any], str]:
    """
    ฟังก์ชันหลักสำหรับเรียกใช้งาน:
    รับคำถามดิบของผู้ใช้ -> คืนค่า (clean_query_for_vector, filters_dict_for_qdrant, query_intent)
    """
    if not raw_query or not raw_query.strip():
        return "", {}, "FACTOID"

    from .extractor import QueryFilterProcessor
    from .normalizer import normalize_user_query

    # 0. Fast-Path Shortcut check (ประหยัดเวลา ~8 วินาทีเมื่อเจอ Pattern ชัดเจน หรือต่อเนื่องจาก Chat History)
    fast_result = _fast_path_check(raw_query, chat_history=chat_history)
    if fast_result:
        return fast_result

    # 1. เรียก Ollama วิเคราะห์คำถามแบบ Dynamic
    llm_result = _call_ollama_for_query_parsing(raw_query, chat_history=chat_history)

    domain_map = {
        "web": ["web", "platform", "เว็บ", "portal", "website", "dashboard", "frontend", "backend", "fullstack", "react", "html", "php"],
        "iot": ["iot", "sensor", "hardware", "arduino", "esp32", "อุปกรณ์", "เซนเซอร์", "watering"],
        "automation": ["automation", "automatic", "อัตโนมัติ", "control", "monitoring"],
        "machine learning": ["machine learning", "ai", "deep learning", "prediction", "ทำนาย", "classification"],
        "energy": ["energy", "saving", "ประหยัดพลังงาน", "access point", "power"],
        "mobile": ["mobile", "app", "apps", "android", "ios", "tracking", "gps", "มือถือ"],
        "healthcare": ["health", "hospital", "patient", "discharge", "โรงพยาบาล", "คนไข้"],
        "cybersecurity": ["security", "network", "penetration", "attack", "ความปลอดภัย"],
    }

    if llm_result:
        norm_query = llm_result.get("normalized_query", "").strip() or raw_query
        filters: dict[str, Any] = {}
        intent = str(llm_result.get("intent", "")).upper().strip()

        advisor_raw = _clean_filter_value(llm_result.get("advisor"))
        if advisor_raw:
            matched_advisor = None
            for ca in metadata_cache.advisors:
                if advisor_raw.lower() == ca.lower() or advisor_raw.lower() in ca.lower():
                    matched_advisor = ca
                    break
            cand_advisor = matched_advisor or advisor_raw
            if _is_advisor_explicitly_in_query(raw_query, cand_advisor, chat_history):
                filters["advisor"] = cand_advisor

        year_raw = _clean_filter_value(llm_result.get("year"))
        if year_raw:
            if _is_year_explicitly_in_query(raw_query, year_raw):
                filters["year"] = year_raw

        title_raw = _clean_filter_value(llm_result.get("project_title"))
        if title_raw:
            matched_title = None
            for ct in metadata_cache.titles:
                if title_raw.lower() == ct.lower():
                    matched_title = ct
                    break
                if ct.lower() in title_raw.lower() or title_raw.lower() in ct.lower():
                    matched_title = ct
                    break
                if len(ct) > 10 and len(title_raw) > 10 and (ct.lower()[:20] == title_raw.lower()[:20]):
                    matched_title = ct
                    break
            cand_title = matched_title or title_raw
            if _is_title_explicitly_in_query(raw_query, cand_title, chat_history):
                filters["project_title"] = cand_title

        author_raw = llm_result.get("author")
        if author_raw:
            raw_authors_list = author_raw if isinstance(author_raw, list) else [author_raw]
            resolved_authors = []
            for item in raw_authors_list:
                cleaned_item = _clean_filter_value(item)
                if not cleaned_item:
                    continue
                for sub_item in cleaned_item.split(","):
                    s = sub_item.strip()
                    if not s or s.lower() in {"null", "none"}:
                        continue
                    matched = None
                    for ca in metadata_cache.authors:
                        if s.lower() == ca.lower() or s.lower() in ca.lower():
                            matched = ca
                            break
                    resolved_name = matched or s
                    if _is_author_explicitly_in_query(raw_query, resolved_name):
                        if resolved_name not in resolved_authors:
                            resolved_authors.append(resolved_name)
            if resolved_authors:
                filters["author"] = resolved_authors if len(resolved_authors) > 1 else resolved_authors[0]

        keywords_raw = _clean_filter_value(llm_result.get("keywords"))
        if keywords_raw and keywords_raw.lower() not in norm_query.lower():
            norm_query = f"{norm_query} {keywords_raw}".strip()

        # Hybrid Enrichment: ถ้า LLM พลาด filter สำคัญ ให้ตัว extractor ดึงเสริม
        clean_norm = normalize_user_query(raw_query)
        processor = QueryFilterProcessor(clean_norm)
        _, rule_filters = processor.parse()
        for k, v in rule_filters.items():
            if k == "author":
                rule_authors = v if isinstance(v, list) else [v]
                valid_rule_authors = [
                    a for a in rule_authors
                    if _is_author_explicitly_in_query(raw_query, str(a))
                ]
                if valid_rule_authors:
                    if k not in filters:
                        filters[k] = valid_rule_authors if len(valid_rule_authors) > 1 else valid_rule_authors[0]
                    else:
                        current_authors = filters[k] if isinstance(filters[k], list) else [filters[k]]
                        merged = list(dict.fromkeys(current_authors + valid_rule_authors))
                        filters[k] = merged if len(merged) > 1 else merged[0]
            elif k == "year":
                if _is_year_explicitly_in_query(raw_query, str(v)):
                    filters[k] = v
            elif k == "advisor":
                if _is_advisor_explicitly_in_query(raw_query, str(v), chat_history):
                    filters[k] = v
            elif k == "project_title":
                if _is_title_explicitly_in_query(raw_query, str(v), chat_history):
                    filters[k] = v

        valid_intents = {"RECOMMENDATION", "EXPLORATORY", "DEEP_DIVE", "COMPARISON", "CODE", "FACTOID"}
        rule_intent = _detect_intent_by_rules(raw_query, project_title_present=bool(filters.get("project_title")))
        if rule_intent in {"COMPARISON", "RECOMMENDATION", "CODE"} or intent not in valid_intents or any(w in raw_query.lower() for w in ["similar", "คล้าย", "เหมือน", "group", "กลุ่ม"]):
            intent = rule_intent

        if filters.get("advisor") and any(w in raw_query.lower() for w in ["projects", "โครงงาน", "โปรเจกต์", "งาน", "มีอะไรบ้าง", "list", "บ้าง"]) and not any(w in raw_query.lower() for w in ["who", "ใคร", "recommend", "แนะนำ"]) and not filters.get("project_title"):
            intent = "EXPLORATORY"

        # Multi-project modes must not lock to a single project or author filter
        if intent == "COMPARISON":
            filters.pop("project_title", None)
            filters.pop("author", None)
            filters.pop("advisor", None)
            matched_in_q = [t for t in metadata_cache.titles if t.lower() in raw_query.lower() or (len(t) > 8 and t[:18].lower() in raw_query.lower())]
            if matched_in_q:
                filters["compared_projects"] = matched_in_q
        elif intent in {"RECOMMENDATION", "EXPLORATORY"}:
            filters.pop("project_title", None)
            filters.pop("author", None)
            if intent == "EXPLORATORY" and "project_type" not in filters:
                for d_kw, d_canon in domain_map.items():
                    pattern = rf"(?:\b|(?<=[\s\u0E00-\u0E7F])){re.escape(d_kw)}(?:\b|(?=[\s\u0E00-\u0E7F]))"
                    if re.search(pattern, raw_query.lower()):
                        filters["project_type"] = d_canon
                        break
            if intent == "RECOMMENDATION":
                # Only keep year if explicitly requested in raw query
                if "year" in filters and not _is_year_explicitly_in_query(raw_query, str(filters["year"])):
                    filters.pop("year", None)
                if "advisor" in filters and not _is_advisor_explicitly_in_query(raw_query, str(filters["advisor"]), chat_history):
                    filters.pop("advisor", None)

        if intent == "RECOMMENDATION":
            domain_keywords = []
            for d_name, kw_list in domain_map.items():
                if any(kw in raw_query.lower() for kw in kw_list):
                    domain_keywords.append(d_name)
            if domain_keywords:
                filters["target_domains"] = domain_keywords

        return norm_query, filters, intent

    # 2. Fallback: กรณี Ollama ปิดอยู่หรือ Timeout ให้สลับไปใช้ In-Memory Cache อัตโนมัติ
    clean_norm = normalize_user_query(raw_query)
    processor = QueryFilterProcessor(clean_norm)
    clean_q, fallback_filters = processor.parse()
    fallback_intent = _detect_intent_by_rules(raw_query, project_title_present=bool(fallback_filters.get("project_title")))
    if fallback_filters.get("advisor") and any(w in raw_query.lower() for w in ["projects", "โครงงาน", "โปรเจกต์", "งาน", "มีอะไรบ้าง", "list", "บ้าง"]) and not any(w in raw_query.lower() for w in ["who", "ใคร", "recommend", "แนะนำ"]) and not fallback_filters.get("project_title"):
        fallback_intent = "EXPLORATORY"
    if fallback_intent == "COMPARISON":
        fallback_filters.pop("project_title", None)
        fallback_filters.pop("author", None)
        fallback_filters.pop("advisor", None)
        matched_in_q = [t for t in metadata_cache.titles if t.lower() in raw_query.lower() or (len(t) > 8 and t[:18].lower() in raw_query.lower())]
        if matched_in_q:
            fallback_filters["compared_projects"] = matched_in_q
    elif fallback_intent in {"RECOMMENDATION", "EXPLORATORY"}:
        fallback_filters.pop("project_title", None)
        fallback_filters.pop("author", None)
        if fallback_intent == "EXPLORATORY" and "project_type" not in fallback_filters:
            for d_kw, d_canon in domain_map.items():
                pattern = rf"(?:\b|(?<=[\s\u0E00-\u0E7F])){re.escape(d_kw)}(?:\b|(?=[\s\u0E00-\u0E7F]))"
                if re.search(pattern, raw_query.lower()):
                    fallback_filters["project_type"] = d_canon
                    break
        if fallback_intent == "RECOMMENDATION":
            if "year" in fallback_filters and not _is_year_explicitly_in_query(raw_query, str(fallback_filters["year"])):
                fallback_filters.pop("year", None)
            if "advisor" in fallback_filters and not _is_advisor_explicitly_in_query(raw_query, str(fallback_filters["advisor"]), chat_history):
                fallback_filters.pop("advisor", None)
            domain_keywords = []
            for d_name, kw_list in domain_map.items():
                if any(kw in raw_query.lower() for kw in kw_list):
                    domain_keywords.append(d_name)
            if domain_keywords:
                fallback_filters["target_domains"] = domain_keywords

    return clean_q, fallback_filters, fallback_intent
