import re
from typing import Any, Optional


_THAI_TECHNICAL_KEYWORDS = [
    "อธิบาย", "ทำงานอย่างไร", "การทำงาน", "ขั้นตอน", "วิธีการ", "สถาปัตยกรรม",
    "โฟลว์", "ผังงาน", "ฮาร์ดแวร์", "ซอฟต์แวร์", "เซนเซอร์", "เซ็นเซอร์",
    "ไมโครคอนโทรลเลอร์", "บอร์ด", "เครื่องมือ", "ฐานข้อมูล", "ตาราง", "โค้ด",
    "ความแม่นยำ", "ผลการทดลอง", "การประเมิน", "เปรียบเทียบ", "ต่างกัน",
    "แนะนำ", "ต่อยอด", "ข้อดี", "ข้อเสีย", "ข้อจำกัด", "รายละเอียดเชิงลึก",
    "ใช้อะไร", "ใช้อุปกรณ์",
]

_ENGLISH_TECHNICAL_KEYWORDS = {
    "how", "why", "work", "works", "working", "explain", "explanation", "describe",
    "architecture", "methodology", "algorithm", "algorithms", "flowchart", "workflow",
    "sensor", "sensors", "microcontroller", "hardware", "software", "tool", "tools",
    "framework", "library", "database", "db", "sql", "table", "schema", "code",
    "accuracy", "result", "results", "evaluation", "testing", "difference", "differences",
    "compare", "comparison", "recommend", "recommendation", "suggest", "suggestion",
    "idea", "future work", "pros", "cons", "advantage", "limitation", "limitations",
    "esp32", "esp8266", "arduino", "lora", "lorawan", "ble", "bluetooth", "iot",
}

_DISQUALIFIED_INTENTS = {"RECOMMENDATION", "COMPARISON", "DEEP_DIVE", "CODE"}


def _has_technical_keywords(query: str, project_title: Optional[str] = None) -> bool:
    """Check if the user is asking a content/technical/reasoning question."""
    q_clean = query.lower()
    if project_title:
        q_clean = q_clean.replace(project_title.lower(), "")

    for kw in _THAI_TECHNICAL_KEYWORDS:
        if kw in q_clean:
            return True

    eng_tokens = set(re.findall(r"[a-z0-9]+", q_clean))
    if any(k in eng_tokens for k in _ENGLISH_TECHNICAL_KEYWORDS):
        return True

    return any(phrase in q_clean for phrase in [
        "ทำงานอย่างไร", "การทำงาน", "สถาปัตยกรรม", "ขั้นตอนการ",
        "เปรียบเทียบ", "ต่างกันอย่างไร", "แนะนำ", "ช่วยแนะนำ",
        "how does", "how it works", "explain the", "compare",
    ])


def _to_thai_year(year_val: Any) -> str:
    """Convert CE year string (e.g. 2020) to BE year (e.g. 2563)."""
    try:
        y = int(str(year_val).strip())
        if 2000 <= y <= 2100:
            return str(y + 543)
    except (ValueError, TypeError):
        pass
    return str(year_val)


def try_generate_template_response(
    question: str,
    rag_context_prep: dict[str, Any],
) -> Optional[str]:
    """
    Direct Deterministic Response Bypass for pure metadata queries.
    
    If the question is a direct factual lookup (advisor projects, project metadata,
    year grouping, or project counts) without technical deep-dive queries,
    this returns a complete, beautifully structured Markdown response in < 5ms,
    bypassing the slow LLM token generation completely.
    """
    if not question or not str(question).strip():
        return None

    intent = rag_context_prep.get("intent", "FACTOID")
    if intent in _DISQUALIFIED_INTENTS:
        return None

    filters = rag_context_prep.get("filters", {})
    citations = rag_context_prep.get("citations", [])
    if not citations:
        return None

    matched_title = filters.get("project_title") or (citations[0].get("project_title") if len(citations) == 1 else None)

    # If the user query contains technical/methodological terms, route to LLM
    if _has_technical_keywords(question, project_title=matched_title):
        return None

    q_lower = question.lower()
    is_count_query = any(k in q_lower for k in ["กี่โครงงาน", "กี่โปรเจกต์", "กี่เรื่อง", "กี่เล่ม", "ทั้งหมดกี่", "how many", "count", "number of"])

    # =========================================================================
    # Case 1: Advisor Projects Listing / Count (1:N Lookup)
    # =========================================================================
    matched_advisor = filters.get("advisor")
    if matched_advisor:
        # Check if asking for advisor's projects (not asking who is the advisor of project X)
        is_asking_advisor_projects = any(k in q_lower for k in [
            "project", "projects", "โครงงาน", "โปรเจกต์", "เรื่องไหน",
            "อะไรบ้าง", "มีอะไรบ้าง", "ที่ปรึกษา", "ดูแล", "list", "ทั้งหมด",
            "ขอรายชื่อ", "รายชื่อ", "กี่เรื่อง", "กี่เล่ม"
        ])

        if is_asking_advisor_projects and not filters.get("project_title"):
            adv_tokens = [
                w.lower()
                for w in re.findall(r"[A-Za-z0-9ก-๙]+", matched_advisor)
                if len(w) >= 3 and w.lower() not in {
                    "ajarn", "aj", "dr", "phd", "prof", "asst", "assoc", "ผศ", "รศ", "ศ", "ดร", "อาจารย์", "mr", "ms", "mrs"
                }
            ]

            def _advisor_matches(c: dict[str, Any]) -> bool:
                adv = str(c.get("advisor") or "").lower()
                comm = str(c.get("committee") or "").lower()
                combined = f"{adv} {comm}"
                if matched_advisor.lower() in combined:
                    return True
                if adv_tokens and any(t in combined for t in adv_tokens):
                    return True
                # If advisor field is empty or missing in chunk, trust the Qdrant filter
                if not c.get("advisor") or c.get("advisor") == "None":
                    return True
                return False

            # Filter citations to ensure they actually list this advisor
            relevant_citations = [c for c in citations if _advisor_matches(c)]
            if not relevant_citations:
                relevant_citations = citations

            # Deduplicate by project_title
            seen_titles = set()
            distinct_projects = []
            for c in relevant_citations:
                t = c.get("project_title") or c.get("source")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    distinct_projects.append(c)

            count = len(distinct_projects)

            if is_count_query:
                titles_bullet = "\n".join([
                    f"- **{p.get('project_title')}** ({p.get('year') or 'ไม่ระบุปี'})"
                    for p in distinct_projects
                ])
                return (
                    f"**{matched_advisor}** เป็นอาจารย์ที่ปรึกษาทั้งหมด **{count} โครงงาน** ในระบบครับ:\n\n"
                    f"{titles_bullet}\n\n"
                    f"> 💡 *สามารถสอบถามรายละเอียดเพิ่มเติมของแต่ละโครงงานได้ครับ เช่น 'ใครเป็นผู้จัดทำโครงงาน {distinct_projects[0].get('project_title')}'*"
                )

            # Markdown Table Output
            rows = []
            for idx, p in enumerate(distinct_projects, 1):
                p_title = p.get("project_title", "-")
                p_year = p.get("year", "-")
                p_prog = p.get("program") or "Computer Engineering"
                p_authors = p.get("author", "-")
                p_source = p.get("source", "เอกสารต้นฉบับ")
                p_pages = p.get("pages_formatted") or ""
                page_info = f" (หน้า {p_pages})" if p_pages and p_pages != "?" else ""
                rows.append(
                    f"| {idx} | **{p_title}** | {p_year} | {p_prog} | {p_authors} | 📄 `{p_source}`{page_info} |"
                )

            table_body = "\n".join(rows)
            sample_title = distinct_projects[0].get("project_title", "") if distinct_projects else ""

            return (
                f"### 📋 รายชื่อโครงงานที่มี **{matched_advisor}** เป็นอาจารย์ที่ปรึกษา (ทั้งหมด {count} โครงงาน)\n\n"
                f"| ลำดับ | ชื่อโครงงาน | ปีการศึกษา | สาขาวิชา | ผู้จัดทำ | เอกสารอ้างอิง |\n"
                f"| :---: | :--- | :---: | :---: | :--- | :--- |\n"
                f"{table_body}\n\n"
                f"> 💡 *ท่านสามารถพิมพ์สอบถามรายละเอียดเชิงลึก เช่น \"อธิบายสถาปัตยกรรมของโครงงาน {sample_title}\" หรือ \"ใช้เซนเซอร์อะไรบ้าง\" ได้ครับ*"
            )

    # =========================================================================
    # Case 2: Project Single Attribute Lookup (1:1 Project Info)
    # =========================================================================
    matched_title = filters.get("project_title")
    if matched_title or (len(citations) == 1 and not filters.get("year")):
        target_citation = citations[0]
        p_title = target_citation.get("project_title") or matched_title or target_citation.get("source")
        advisor = target_citation.get("advisor")
        committee = target_citation.get("committee")
        if not committee or committee == "None":
            committee = "ไม่ระบุในเอกสาร"

        if not advisor or advisor == "None":
            if committee != "ไม่ระบุในเอกสาร":
                first_comm = committee.split(",")[0].strip()
                advisor = f"{first_comm} (จากรายชื่อคณะกรรมการ)"
            else:
                advisor = "ไม่ระบุในเอกสาร"

        authors = target_citation.get("author")
        if not authors or authors == "None":
            authors = "ไม่ระบุในเอกสาร"
        year = target_citation.get("year") or "ไม่ระบุปี"
        if year == "None":
            year = "ไม่ระบุปี"
        thai_year = _to_thai_year(year) if year != "ไม่ระบุปี" else "-"
        school = target_citation.get("school") or "Applied Digital Technology"
        program = target_citation.get("program") or "Computer Engineering"
        source = target_citation.get("source", "เอกสารต้นฉบับ")
        pages = target_citation.get("pages_formatted") or ""
        page_info = f" (หน้า {pages})" if pages and pages != "?" else ""

        # Specific Question: Who is Advisor?
        if any(k in q_lower for k in ["advisor", "ที่ปรึกษา", "ใครเป็นที่ปรึกษา", "อาจารย์ที่ปรึกษาคือใคร", "who is the advisor", "who is advisor"]):
            return (
                f"อาจารย์ที่ปรึกษาของโครงงาน **{p_title}** คือ **{advisor}** ครับ\n\n"
                f"- **คณะกรรมการตรวจโครงงาน (Committee)**: {committee}\n"
                f"- **ปีการศึกษา**: {year} (พ.ศ. {thai_year})\n"
                f"- **เอกสารอ้างอิง**: 📄 `{source}`{page_info}"
            )

        # Specific Question: Who are Authors?
        if any(k in q_lower for k in ["ผู้จัดทำ", "ใครทำ", "ใครจัดทำ", "ผู้แต่ง", "author", "authors", "who created", "who made", "who wrote"]):
            return (
                f"ผู้จัดทำโครงงาน **{p_title}** ได้แก่:\n\n"
                f"**{authors}**\n\n"
                f"- **อาจารย์ที่ปรึกษา**: {advisor}\n"
                f"- **ปีการศึกษา**: {year} (พ.ศ. {thai_year})\n"
                f"- **เอกสารอ้างอิง**: 📄 `{source}`{page_info}"
            )

        # Specific Question: What Year?
        if any(k in q_lower for k in ["ปีไหน", "ปีอะไร", "ปีการศึกษา", "ทำปีไหน", "when", "what year"]):
            return (
                f"โครงงาน **{p_title}** จัดทำขึ้นในปีการศึกษา **{year}** (พ.ศ. {thai_year}) ครับ\n\n"
                f"- **อาจารย์ที่ปรึกษา**: {advisor}\n"
                f"- **ผู้จัดทำ**: {authors}\n"
                f"- **เอกสารอ้างอิง**: 📄 `{source}`{page_info}"
            )

        # Specific Question: Committee?
        if any(k in q_lower for k in ["กรรมการ", "คณะกรรมการ", "committee", "examiner", "examining"]):
            return (
                f"คณะกรรมการประเมินโครงงาน **{p_title}** ได้แก่:\n\n"
                f"- **อาจารย์ที่ปรึกษา (Advisor)**: {advisor}\n"
                f"- **คณะกรรมการ (Committee)**: {committee}\n\n"
                f"- **เอกสารอ้างอิง**: 📄 `{source}`{page_info}"
            )

        # General Project Overview Info
        if any(k in q_lower for k in ["ข้อมูล", "รายละเอียดเบื้องต้น", "about", "overview", "คือใคร", "เรื่องอะไร"]):
            return (
                f"ข้อมูลเบื้องต้นของโครงงาน **{p_title}**:\n\n"
                f"- **อาจารย์ที่ปรึกษา**: {advisor}\n"
                f"- **คณะกรรมการประเมิน (Committee)**: {committee}\n"
                f"- **ผู้จัดทำ**: {authors}\n"
                f"- **ปีการศึกษา**: {year} (พ.ศ. {thai_year})\n"
                f"- **สำนักวิชา / สาขาวิชา**: {school} / {program}\n"
                f"- **เอกสารต้นฉบับ**: 📄 `{source}`{page_info}\n\n"
                f"> 💡 *หากต้องการทราบข้อมูลสเปกฮาร์ดแวร์ เทคโนโลยีที่ใช้ หรือการทำงาน สามารถพิมพ์ถามได้เลยครับ*"
            )

    # =========================================================================
    # Case 3: Year Grouping Listing (Group Listing)
    # =========================================================================
    matched_year = filters.get("year")
    if matched_year and not filters.get("project_title"):
        is_year_listing = any(k in q_lower for k in [
            "โครงงาน", "โปรเจกต์", "project", "projects", "อะไรบ้าง",
            "มีอะไรบ้าง", "รายชื่อ", "ทั้งหมด", "list", "มีกี่", "กี่โครงงาน"
        ])
        if is_year_listing:
            # Deduplicate citations by project
            seen_titles = set()
            distinct_projects = []
            for c in citations:
                t = c.get("project_title") or c.get("source")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    distinct_projects.append(c)

            count = len(distinct_projects)
            thai_year = _to_thai_year(matched_year)

            if is_count_query:
                return f"ในปีการศึกษา **{matched_year}** (พ.ศ. {thai_year}) มีโครงงานในระบบทั้งหมด **{count} โครงงาน** ครับ"

            items = []
            for idx, p in enumerate(distinct_projects, 1):
                p_title = p.get("project_title", "-")
                p_authors = p.get("author", "-")
                p_adv = p.get("advisor", "-")
                p_source = p.get("source", "")
                p_pages = p.get("pages_formatted") or ""
                page_info = f" (หน้า {p_pages})" if p_pages and p_pages != "?" else ""
                items.append(
                    f"{idx}. **{p_title}**\n"
                    f"   - **ผู้จัดทำ**: {p_authors}\n"
                    f"   - **อาจารย์ที่ปรึกษา**: {p_adv}\n"
                    f"   - **เอกสาร**: 📄 `{p_source}`{page_info}"
                )

            list_body = "\n\n".join(items)
            return (
                f"### 🎓 รายชื่อโครงงานประจำปีการศึกษา **{matched_year}** (พ.ศ. {thai_year}) ทั้งหมด {count} โครงงาน\n\n"
                f"{list_body}\n\n"
                f"> 💡 *พิมพ์ชื่อโครงงานเพื่อดูรายละเอียดเชิงลึก เช่น เซนเซอร์ ฮาร์ดแวร์ หรือสถาปัตยกรรมระบบได้ครับ*"
            )

    # =========================================================================
    # Case 4: Course Grouping (e.g. Pre-Project CPE491 vs Senior Project CPE492)
    # =========================================================================
    # Case 4: School / Program Grouping
    # =========================================================================
    _PROG_QUERY_MAP = [
        ("Software Engineering", ["software engineering", "วิศวกรรมซอฟต์แวร์"]),
        ("Multimedia Technology & Animation", ["multimedia", "animation", "มัลติมีเดีย", "แอนิเมชัน"]),
        ("Digital Engineering & Communications", ["digital engineering", "วิศวกรรมดิจิทัล"]),
        ("Digital Technology for Business Innovation", ["business innovation", "นวัตกรรมทางธุรกิจ"]),
        ("Computer Engineering", ["computer engineering", "วิศวกรรมคอมพิวเตอร์"]),
    ]
    for prog_canonical, prog_triggers in _PROG_QUERY_MAP:
        if any(pt in q_lower for pt in prog_triggers) and any(w in q_lower for w in ["สาขา", "โครงงาน", "โปรเจกต์", "project", "projects", "มีอะไรบ้าง", "กี่เรื่อง"]):
            matching = [
                c for c in citations
                if prog_canonical.lower() in str(c.get("program", "")).lower()
                or not c.get("program")
            ]
            if matching:
                seen_titles = set()
                distinct = []
                for c in matching:
                    t = c.get("project_title") or c.get("source")
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        distinct.append(c)
                if distinct and not _has_technical_keywords(question):
                    items = []
                    for idx, p in enumerate(distinct, 1):
                        items.append(
                            f"{idx}. **{p.get('project_title')}** (ปี {p.get('year') or '-'})\n"
                            f"   - **อาจารย์ที่ปรึกษา**: {p.get('advisor') or '-'}\n"
                            f"   - **ผู้จัดทำ**: {p.get('author') or '-'}\n"
                            f"   - **เอกสาร**: 📄 `{p.get('source')}`"
                        )
                    return (
                        f"### 🎓 รายชื่อโครงงานในสาขาวิชา **{prog_canonical}** (ทั้งหมด {len(distinct)} โครงงาน)\n\n"
                        + "\n\n".join(items)
                    )

    if any(k in q_lower for k in [
        "สำนักวิชา", "applied digital technology", "school of applied digital technology",
        "school of information technology", "สำนักไอที", "เทคโนโลยีดิจิทัลประยุกต์"
    ]):
        seen_titles = set()
        distinct = []
        for c in citations:
            t = c.get("project_title") or c.get("source")
            if t and t not in seen_titles:
                seen_titles.add(t)
                distinct.append(c)

        if distinct and not _has_technical_keywords(question):
            items = []
            for idx, p in enumerate(distinct, 1):
                items.append(
                    f"{idx}. **{p.get('project_title')}** (ปี {p.get('year') or '-'})\n"
                    f"   - **สาขาวิชา**: {p.get('program') or 'Computer Engineering'}\n"
                    f"   - **อาจารย์ที่ปรึกษา**: {p.get('advisor') or '-'}\n"
                    f"   - **เอกสาร**: 📄 `{p.get('source')}`"
                )
            return (
                f"### 🏛️ รายชื่อโครงงานภายใต้ **สำนักวิชา Applied Digital Technology** (ทั้งหมด {len(distinct)} โครงงาน)\n\n"
                + "\n\n".join(items)
            )

    return None
