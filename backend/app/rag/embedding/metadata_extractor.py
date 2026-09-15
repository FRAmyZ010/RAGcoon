import re

_DEGREE_PATTERN = re.compile(r"\b(BACHELOR|MASTER|DOCTOR|DIPLOMA)\b", re.IGNORECASE)
_NAME_PREFIX_PATTERN = re.compile(r"(Mr\.|Ms\.|Miss)\s+[A-Z].*", re.IGNORECASE)
_TITLE_WORDS = {
    "access", "agency", "application", "attack", "computer", "cybersecurity",
    "development", "energy", "for", "in", "management", "monitoring", "of",
    "online", "project", "system", "the", "vehicle", "wlan",
}


def _clean_name_spacing(name: str | None) -> str | None:
    """Clean missing spaces after dots and in CamelCase/TitleCase words from OCR/PDF."""
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip(" .:-()[]")
    # 1. Add space between dot and following letter (e.g. "Asst.Prof." -> "Asst. Prof.")
    cleaned = re.sub(r"\.([A-Za-z])", r". \1", cleaned)
    # 2. Add space between lowercase and uppercase letter (e.g. "SurapolVorapatratorn" -> "Surapol Vorapatratorn")
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    # 3. Clean multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned or None


def _looks_like_author_name(line: str) -> bool:
    if _NAME_PREFIX_PATTERN.fullmatch(line):
        return True

    words = re.findall(r"[A-Za-z]+", line)
    return (
        line.isupper()
        and 2 <= len(words) <= 3
        and not any(word.lower() in _TITLE_WORDS for word in words)
    )


def _extract_title_and_authors(lines: list[str]) -> tuple[list[str], list[str]]:
    """Use the degree heading to separate wrapped titles from author names."""
    degree_index = next(
        (index for index, line in enumerate(lines) if _DEGREE_PATTERN.search(line)),
        None,
    )
    if degree_index is None:
        return lines[:1], []

    author_start = degree_index
    while author_start > 0 and _looks_like_author_name(lines[author_start - 1]):
        author_start -= 1

    authors = lines[author_start:degree_index]
    title_lines = lines[:author_start]
    if title_lines and authors:
        return title_lines, authors

    return lines[:1], []


def _extract_approval_committee(lines: list[str]) -> tuple[str | None, list[str]]:
    """Extract names from the approval page's labelled committee entries."""
    label_pattern = re.compile(r"\b(ADVISOR|COMMITTEE)\b", re.IGNORECASE)
    label_lines = [
        (line_index, match)
        for line_index, line in enumerate(lines)
        for match in [label_pattern.search(line)]
        if match
    ]
    advisor: str | None = None
    committee: list[str] = []

    for label_index, (line_index, label) in enumerate(label_lines):
        next_line_index = (
            label_lines[label_index + 1][0]
            if label_index + 1 < len(label_lines)
            else len(lines)
        )
        block = lines[line_index:next_line_index]
        candidates: list[str] = []
        for block_index, line in enumerate(block):
            if block_index == 0:
                line = line[label.end():]
            candidates.extend(
                value.strip(" .:-")
                for value in re.findall(r"\(([^()]*)\)", line)
                if value.strip(" .:-")
            )
            cleaned = re.sub(r"[.:-]+", " ", line).strip()
            if cleaned and not re.search(
                r"ADVISOR|COMMITTEE|EXAMINING", cleaned, re.IGNORECASE
            ):
                candidates.append(cleaned)

        name = next(
            (
                _clean_name_spacing(candidate)
                for candidate in candidates
                if candidate and len(_clean_name_spacing(candidate) or "") > 3
                and re.fullmatch(r"[A-Za-z][A-Za-z .,'()&-]*", _clean_name_spacing(candidate) or "")
            ),
            None,
        )
        if name and name != advisor:
            if label.group(1).upper() == "ADVISOR":
                advisor = name
            else:
                committee.append(name)

    return advisor, committee


def extract_project_metadata(first_page_text: str) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {
        "project_title": None,
        "author": None,
        "advisor": None,
        "committee": None,
        "keywords": None,
        "year": None
    }

    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]

    if len(lines) >= 1:
        # --- Project Title ---
        title_lines, authors = _extract_title_and_authors(lines)
        title_limit = len(title_lines)
        title = " ".join(title_lines)
        
        # แก้จุดที่ 1: ย้าย (?i) มาไว้หน้าสุด
        proposal_match = re.search(
            r"\(Project\s+Proposal\)", first_page_text, re.IGNORECASE
        )
        if proposal_match and proposal_match.group(0).lower() not in title.lower():
            title_limit = 2
            title = " ".join(lines[:title_limit])
            title = f"{title} {proposal_match.group(0)}"
        
        metadata["project_title"] = title

        # --- Author ---
        authors = list(authors)
        potential_author_lines = lines[title_limit : title_limit + 8] 
        
        for line in potential_author_lines:
            # แก้จุดที่ 2: ใช้ re.IGNORECASE แทนการใส่ (?i) ใน string
            if re.search(r"Bachelor", line, re.IGNORECASE):
                break
            
            if re.search(r"Advisor|Keywords?|Year", line, re.IGNORECASE):
                break

            # รูปแบบชื่อตัวพิมพ์ใหญ่
            is_uppercase_name = _looks_like_author_name(line)
            # แก้จุดที่ 3: ย้าย (?i) มาหน้าสุดสำหรับ Prefix
            is_prefix_name = _NAME_PREFIX_PATTERN.match(line)

            if (is_uppercase_name or is_prefix_name) and line not in authors:
                authors.append(line)
        
        if authors:
            metadata["author"] = ", ".join(authors)

    # --- 3. Advisor and Committee ---
    found_advisor: str | None = None
    found_committee: list[str] = []
    for i, line in enumerate(lines):
        # ปรับให้หาคำว่า Supervisory ก็พอ เผื่อ Committee มันกระเด็นไปบรรทัดอื่น
        if re.search(r"Supervisory", line, re.IGNORECASE):
            # ตรวจสอบบรรทัดปัจจุบันและบรรทัดถัดไปที่อยู่ในส่วนคณะกรรมการ
            search_scope = lines[i : i + 8]
            combined_context = " ".join(search_scope)

            # # เช็คจาก Dictionary (Priority 1)
            # for keyword, full_name in advisor_map.items():
            #     if re.search(keyword, combined_context, re.IGNORECASE):
            #         found_advisor = full_name
            #         break
            
            # if found_advisor: break

            # # เช็คจากวงเล็บ (Priority 2)
            # bracket_match = re.search(r"\(([^)]+)\)", combined_context)
            # if bracket_match and len(bracket_match.group(1)) > 5:
            #     found_advisor = bracket_match.group(1).strip()
            #     break
            
            # เช็คระหว่างคำว่า Supervisory Committee...Advisor (Priority 3)
            # ใช้ \s+ เพื่อรองรับทั้งช่องว่างเดียว หรือการขึ้นบรรทัดใหม่ระหว่างคำ
            mid_match = re.search(
                r"Supervisory\s+Committee\s+(.*?)\s+Advisor",
                combined_context,
                re.IGNORECASE,
            )

            if mid_match:
                            # ดึงข้อความที่อยู่ตรงกลางระหว่างคำว่า Committee กับ Advisor
                            advisor_name = mid_match.group(1).strip()
                            # ทำความสะอาดเศษอักขระที่อาจติดมาจากการสแกน เช่น จุด หรือ เครื่องหมายลบ
                            advisor_name = advisor_name.strip(" .:-")
                            
                            found_advisor = advisor_name

            for committee_line in search_scope:
                committee_line = re.sub(
                    r"^Supervisory\s+Committee\s*",
                    "",
                    committee_line,
                    flags=re.IGNORECASE,
                )
                committee_match = re.search(
                    r"\bCommittee\b",
                    committee_line,
                    re.IGNORECASE,
                )
                if not committee_match:
                    continue

                committee_name = committee_line[:committee_match.start()].strip(" .:-")
                if committee_name and committee_name.lower() != "supervisory":
                    found_committee.append(committee_name)

            break
    if found_advisor is None and found_committee == []:
        approval_advisor, approval_committee = _extract_approval_committee(lines)
        found_advisor = approval_advisor
        found_committee = approval_committee

    cleaned_advisor = _clean_name_spacing(found_advisor)
    metadata["advisor"] = cleaned_advisor
    if found_committee:
        cleaned_committee_list = [
            _clean_name_spacing(c) for c in found_committee
            if _clean_name_spacing(c)
        ]
        metadata["committee"] = ", ".join(dict.fromkeys(cleaned_committee_list))

    # --- ส่วน Keywords (Logic ใหม่: สแกนทีละบรรทัด) ---
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    found_keywords: list[str] = []

    for line in lines:
        # 1. หาบรรทัดที่มีคำว่า Keyword (รองรับตัวหนา/พิมพ์เล็ก-ใหญ่/มีหรือไม่มี s)
        if re.search(r"\bKeywords?\b", line, re.IGNORECASE):
            # ลองดึงข้อมูลที่อาจจะอยู่ในบรรทัดเดียวกันมาด้วย (หลังเครื่องหมาย :)
            content_after_header = re.sub(
                r"Keywords?\s*[:\-]?\s*", "", line, flags=re.IGNORECASE
            ).strip()
            if content_after_header:
                found_keywords.append(content_after_header)
            continue
        
        # # 2. ถ้าเจอหัวข้อแล้ว ให้เก็บบรรทัดถัดๆ มา
        # if start_collecting:
        #     # จุดหยุด: ถ้าเจอปี ค.ศ. หรือ บรรทัดที่เป็นหัวข้ออื่น (เช่น Advisor หรือ Year)
        #     if re.search(r"Advisor|Year|\b20[12]\d\b", line, re.IGNORECASE):
        #         break
            
        #     # ถ้าบรรทัดนี้ไม่ใช่หัวข้ออื่น ให้ถือว่าเป็นเนื้อหาของ Keywords
        #     found_keywords.append(line)

    if found_keywords:
        # รวมบรรทัดเข้าด้วยกันและทำความสะอาด
        full_keywords = " ".join(found_keywords)
        # ลบช่องว่างส่วนเกินและจุดปิดท้าย
        metadata["keywords"] = re.sub(r'\s+', ' ', full_keywords).strip(' .')
    # Year
    year_match = re.search(r"\b(20[12]\d)\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group(1)

    return metadata
