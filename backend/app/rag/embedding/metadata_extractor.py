import re

_DEGREE_PATTERN = re.compile(
    r"\b(?:B[AE]CHELOR|MASTER|DOCTOR|DIPLOMA|SUBMITTED\s+TO|HAS\s+BEE?N|APPROVED\s+TO\s+BE|A\s+SENIOR\s+PROJECT|THIS\s+SENIOR\s+PROJECT|A\s+COMPUTER\s+ENGINEERING\s+PROJECT|THIS\s+COMPUTER\s+ENGINEERING\s+PROJECT)\b",
    re.IGNORECASE,
)
_NAME_PREFIX_PATTERN = re.compile(r"^(?:Mr\.|Ms\.|Miss|Mrs\.)\s+[A-Z].*", re.IGNORECASE)

_DOC_HEADER_PATTERN = re.compile(
    r"^\(?\s*(?:PROJECT\s+PROPO?S[AO]?L|PRE[\-\s]PROJECT(?:\s+PROPO?S[AO]?L)?|SENIOR\s+PROJECT(?:\s+PROPO?S[AO]?L)?|FINAL\s+PROJECT(?:\s+REPORT)?|FINAL\s+REPORT)\s*\)?\s*[:\-]?",
    re.IGNORECASE,
)

_TITLE_WORDS = {
    "access", "acknowledgement", "agency", "algorithm", "algorithms", "analysis",
    "application", "applications", "approach", "attack", "attendance", "automation",
    "avoiding", "beacon", "ble", "bluetooth", "bts", "car", "case", "checking",
    "cisco", "classification", "clustering", "collector", "computer", "contents",
    "copyright", "ctf", "cybersecurity", "department", "design", "detection",
    "detector", "development", "device", "discharge", "dust", "energy", "engineering",
    "evaluation", "examination", "faculty", "fah", "flow", "following", "for",
    "forms", "framework", "gem", "hardware", "identity", "illegitimate", "in",
    "information", "intelligent", "intersection", "learning", "liquid", "locating",
    "location", "logo", "lorawan", "luang", "machine", "mae", "malicious", "management",
    "meter", "mfu", "microcontroller", "mini", "model", "models", "monitoring",
    "network", "networks", "obstacles", "of", "on", "online", "opt-in", "organizational",
    "overview", "page", "pages", "penetration", "personalized", "planning", "platform",
    "point", "points", "prediction", "price", "program", "project", "proposal",
    "propsal", "quality", "range", "recommendation", "robot", "saving", "school",
    "security", "sensor", "sensors", "service", "services", "servicve", "smart",
    "software", "stock", "study", "system", "systems", "technology", "testing",
    "the", "tracking", "traffic", "transit", "travel", "university", "using",
    "vehicle", "wallpaper", "watering", "web", "website", "wireless", "wlan",
}

_KNOWN_PROGRAMS = [
    (
        "Digital Technology for Business Innovation",
        re.compile(
            r"\b(?:Digital\s+Technology\s+(?:for\s+)?Business\s+Innovation|เทคโนโลยีดิจิทัลเพื่อนวัตกรรมทางธุรกิจ)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Digital Engineering & Communications",
        re.compile(
            r"\b(?:Digital\s+Engineering\s*(?:&|and)\s*Communications?|Digital\s+Engineering|วิศวกรรมดิจิทัล(?:\s*และการสื่อสาร)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Multimedia Technology & Animation",
        re.compile(
            r"\b(?:Multimedia\s+Technology\s*(?:&|and)\s*Animation|Multimedia\s+Technology|เทคโนโลยีมัลติมีเดีย(?:\s*และแอนิเมชัน)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Software Engineering",
        re.compile(
            r"\b(?:Software\s+Engineering|วิศวกรรมซอฟต์แวร์)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Computer Engineering",
        re.compile(
            r"\b(?:Computer\s+Engineering|วิศวกรรมคอมพิวเตอร์|CPE\s*49[12])\b",
            re.IGNORECASE,
        ),
    ),
]


def _clean_name_spacing(name: str | None) -> str | None:
    """Clean missing spaces after dots and in CamelCase/TitleCase words from OCR/PDF."""
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip(" .:-()[]")
    cleaned = re.sub(r"\.([A-Za-z])", r". \1", cleaned)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned or None


def _looks_like_author_name(line: str) -> bool:
    line_clean = line.strip(" .:-")
    if _NAME_PREFIX_PATTERN.match(line_clean):
        return True
    words = re.findall(r"[A-Za-z]+", line_clean)
    if not (1 <= len(words) <= 4):
        return False
    if any(w.lower() in _TITLE_WORDS for w in words):
        return False
    # If first word is capitalized and all words are letters (e.g. Vasawat prapachaimongkol or VASAWAT PRAPACHAIMONGKOL)
    if words[0][0].isupper() and all(len(w) >= 2 for w in words):
        return True
    is_caps = line_clean.isupper()
    is_title_case = all(w[0].isupper() for w in words if w)
    return is_caps or is_title_case


def clean_project_title(title: str | None) -> str | None:
    """Clean header labels, typos, and extra punctuation from extracted project titles."""
    if not title or not isinstance(title, str):
        return None
    cleaned = re.sub(r"^\s*Title\s*[:\-]?\s*", "", title.strip(), flags=re.IGNORECASE)
    cleaned = _DOC_HEADER_PATTERN.sub("", cleaned).strip(" .:-")
    cleaned = re.sub(
        r"^\(?\s*(?:PROJECT\s+PROPO?S[AO]?L|PRE[\-\s]PROJECT|SENIOR\s+PROJECT)\s*\)?\b\s*[:\-]?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip(" .:-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or cleaned.upper() in {"PROJECT PROPOSAL", "(PROJECT PROPOSAL)", "(PROJECT PROPSAL)", "PROPOSAL"}:
        return None
    return cleaned if len(cleaned) >= 5 else None


def _extract_title_and_authors(lines: list[str]) -> tuple[list[str], list[str]]:
    """Use the degree heading to separate wrapped titles from author names."""
    filtered: list[str] = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if re.match(r"^(\d+|[ivxlcdm]+)$", s, re.IGNORECASE):
            continue
        if _DOC_HEADER_PATTERN.match(s) and len(filtered) == 0:
            continue
        filtered.append(s)

    if not filtered:
        return [], []

    degree_index = next(
        (index for index, line in enumerate(filtered) if _DEGREE_PATTERN.search(line)),
        None,
    )
    if degree_index is None:
        boundary = len(filtered)
    else:
        boundary = degree_index

    author_start = boundary
    while author_start > 0 and _looks_like_author_name(filtered[author_start - 1]):
        author_start -= 1

    authors = filtered[author_start:boundary]
    title_lines = filtered[:author_start]
    return title_lines, authors


def _extract_approval_committee(lines: list[str]) -> tuple[str | None, list[str]]:
    """Extract names from the approval page's labelled committee entries."""
    label_pattern = re.compile(r"\b(ADVIS[OE]R|COMMITTEE)\b", re.IGNORECASE)
    label_lines = [
        (line_index, match)
        for line_index, line in enumerate(lines)
        if not re.search(r"\b(?:EXAMINING|SUPERVISORY)\s+COMMITTEE\b", line, re.IGNORECASE)
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
                r"ADVIS[OE]R|COMMITTEE|EXAMINING|SUPERVISORY", cleaned, re.IGNORECASE
            ):
                candidates.append(cleaned)

        name = next(
            (
                _clean_name_spacing(candidate)
                for candidate in candidates
                if candidate and len(_clean_name_spacing(candidate) or "") > 3
                and re.fullmatch(r"[A-Za-z][A-Za-z .,'()&-]*", _clean_name_spacing(candidate) or "")
                and not any(w.lower() in _TITLE_WORDS for w in re.findall(r"[A-Za-z]+", candidate))
            ),
            None,
        )
        if name and name != advisor:
            if label.group(1).upper() in ("ADVISOR", "ADVISER"):
                advisor = name
            else:
                committee.append(name)

    return advisor, committee


def extract_project_metadata(first_page_text: str, filename: str | None = None) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {
        "project_title": None,
        "author": None,
        "advisor": None,
        "committee": None,
        "keywords": None,
        "year": None,
        "school": None,
        "program": None,
        "course": None,
    }

    # Skip front-matter pages that should not extract titles/authors (e.g. acknowledgements, table of contents)
    header_check = first_page_text[:300].strip()
    if re.search(r"\b(?:ACKNOWLEDGEMENTS?|TABLE\s+OF\s+CONTENTS|กิตติกรรมประกาศ|สารบัญ)\b", header_check, re.IGNORECASE):
        return metadata

    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]

    if len(lines) >= 1:
        # --- Project Title ---
        title_lines, authors = _extract_title_and_authors(lines)
        title_limit = len(title_lines)
        raw_title = " ".join(title_lines)
        clean_title = clean_project_title(raw_title)
        metadata["project_title"] = clean_title

        # --- Author ---
        authors = list(authors)
        if not authors:
            potential_author_lines = lines[title_limit : title_limit + 8] 
            for line in potential_author_lines:
                if _DEGREE_PATTERN.search(line) or re.search(r"Advis[oe]r|Keywords?|Year", line, re.IGNORECASE):
                    break
                is_uppercase_name = _looks_like_author_name(line)
                is_prefix_name = _NAME_PREFIX_PATTERN.match(line)
                if (is_uppercase_name or is_prefix_name) and line not in authors:
                    authors.append(line)
        
        cleaned_authors = []
        for a in authors:
            ca = _clean_name_spacing(a)
            if ca and ca not in cleaned_authors:
                cleaned_authors.append(ca)

        if cleaned_authors:
            metadata["author"] = ", ".join(cleaned_authors)

    # --- 3. Advisor and Committee ---
    found_advisor: str | None = None
    found_committee: list[str] = []
    for i, line in enumerate(lines):
        if re.search(r"Supervisory", line, re.IGNORECASE):
            search_scope = lines[i : i + 8]
            combined_context = " ".join(search_scope)
            mid_match = re.search(
                r"Supervisory\s+Committee\s+(.*?)\s+Advis[oe]r",
                combined_context,
                re.IGNORECASE,
            )

            if mid_match:
                advisor_name = mid_match.group(1).strip()
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

    if found_advisor is None or not found_committee:
        approval_advisor, approval_committee = _extract_approval_committee(lines)
        if found_advisor is None and approval_advisor:
            found_advisor = approval_advisor
        if not found_committee and approval_committee:
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

    # --- Program (สาขาวิชา) & School (สำนักวิชา) ---
    # ตรวจสอบ 5 สาขาวิชา:
    # 1. Computer Engineering
    # 2. Software Engineering
    # 3. Multimedia Technology & Animation
    # 4. Digital Engineering & Communications
    # 5. Digital Technology for Business Innovation
    # หากพบในหน้าแรก ให้ระบุเป็นสาขา และกำหนดสำนักวิชาเป็น "Applied Digital Technology"
    matched_program = None
    for prog_name, pattern in _KNOWN_PROGRAMS:
        if pattern.search(first_page_text) or (filename and pattern.search(filename)):
            matched_program = prog_name
            break

    if matched_program:
        metadata["program"] = matched_program
        metadata["school"] = "Applied Digital Technology"
    else:
        # Fallback หากไม่ตรงกับ 5 สาขาวิชาหลัก
        prog_match = re.search(
            r"\b(?:IN|OF)\s+([A-Za-z\s]+?)(?=\s+MAE|\s+20\d\d|\s+THIS|\s*$)",
            first_page_text,
            re.IGNORECASE,
        )
        if prog_match:
            metadata["program"] = prog_match.group(1).title().strip()

        school_match = re.search(
            r"\b(?:SCHOOL|FACULTY)\s+OF\s+([A-Za-z\s]+?)(?=\s+MAE|\s+20\d\d|\s+B[AE]CHELOR|\s+THIS|\s*$)",
            first_page_text,
            re.IGNORECASE,
        )
        if school_match:
            raw_school = school_match.group(1).strip()
            if any(k in raw_school.lower() for k in ["information", "applied digital", "digital"]):
                metadata["school"] = "Applied Digital Technology"
            else:
                metadata["school"] = f"School of {raw_school.title()}"
        elif re.search(r"สำนักวิชา\s*([ก-๙A-Za-z\s]+)", first_page_text):
            th_school = re.search(r"สำนักวิชา\s*([ก-๙A-Za-z\s]+)", first_page_text).group(1).strip()
            if any(k in th_school for k in ["เทคโนโลยีสารสนเทศ", "เทคโนโลยีดิจิทัลประยุกต์"]):
                metadata["school"] = "Applied Digital Technology"
            else:
                metadata["school"] = f"สำนักวิชา{th_school}"

    # --- Course / รายวิชา / ประเภทโครงงาน ---
    combined_ctx = f"{filename or ''} {first_page_text}"
    if re.search(r"(?:PRE[\-\s_]*PROJECT|CPE\s*491|1301491)", combined_ctx, re.IGNORECASE):
        metadata["course"] = "Pre-Project (CPE491)"
    elif re.search(r"(?:SENIOR[\-\s_]*PROJECT|CPE\s*492|1301492|COMPUTER\s+ENGINEERING\s+PROJECT)", combined_ctx, re.IGNORECASE):
        metadata["course"] = "Senior Project (CPE492)"
    elif metadata["project_title"]:
        metadata["course"] = "Senior Project (CPE492)"

    return metadata
