import re

_DEGREE_PATTERN = re.compile(
    r"\b(?:B[AE]CHELOR|MASTER|DOCTOR|DIPLOMA|SUBMITTED\s+TO|HAS\s+BEE?N|APPROVED\s+TO\s+BE|A\s+SENIOR\s+PROJECT|THIS\s+SENIOR\s+PROJECT|A\s+COMPUTER\s+ENGINEERING\s+PROJECT|THIS\s+COMPUTER\s+ENGINEERING\s+PROJECT)\b",
    re.IGNORECASE,
)
_NAME_PREFIX_PATTERN = re.compile(r"^(?:Mr\.|Ms\.|Miss|Mrs\.)\s+[A-Z].*", re.IGNORECASE)
_KEYWORD_LABEL = re.compile(r"^(?:Keywords?|คำสำคัญ)\b\s*[:：\-]?\s*(.*)$", re.IGNORECASE)
_KEYWORD_STOP = re.compile(
    r"^(?:ABSTRACT|บทคัดย่อ|CHAPTER|REFERENCES|ACKNOWLEDGEMENTS?|TABLE\s+OF\s+CONTENTS|สารบัญ)\b",
    re.IGNORECASE,
)

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


_FIELD_LABEL_PREFIX = re.compile(
    r"^(?:Title|Authors?|Degree|Advisor|Adviser|Committee|Supervisory(?:\s+Committee)?)\s*[:\-.]?\s*",
    re.IGNORECASE,
)
_TRAILING_ROLE = re.compile(r"\s+(?:Advisor|Adviser|Committee)\s*$", re.IGNORECASE)
_ROLE_JUNK_TOKEN = re.compile(
    r"\b(?:Supervisory|Committee|Committ(?:ee)?|Advisor|Adviser)\b",
    re.IGNORECASE,
)
_SUPERVISORY_STOP = re.compile(
    r"^(?:Abstract|บทคัดย่อ|Keywords?|คำสำคัญ|Contents|สารบัญ)\b",
    re.IGNORECASE,
)


def _clean_name_spacing(name: str | None) -> str | None:
    """Clean missing spaces after dots and in CamelCase/TitleCase words from OCR/PDF."""
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip(" .:-()[]")
    cleaned = re.sub(r"\.([A-Za-z])", r". \1", cleaned)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned or None


def _strip_field_label(line: str) -> str:
    """Remove leading metadata labels such as Author / Title from a line."""
    return _FIELD_LABEL_PREFIX.sub("", line.strip()).strip(" .:-")


def _finalize_person_name(raw: str | None) -> str | None:
    """Strip labels/role junk then normalize OCR spacing."""
    if not raw or not isinstance(raw, str):
        return None
    cleaned = _strip_field_label(raw)
    cleaned = _TRAILING_ROLE.sub("", cleaned).strip(" .:-")
    cleaned = _ROLE_JUNK_TOKEN.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return _clean_name_spacing(cleaned)


def _is_valid_author_name(name: str | None) -> bool:
    """Author kept when length > 5; single-token given names are allowed."""
    if not name:
        return False
    if len(name) <= 5:
        return False
    if _ROLE_JUNK_TOKEN.search(name):
        return False
    return bool(re.search(r"[A-Za-zก-๙]", name))


def _is_valid_supervisory_name(name: str | None) -> bool:
    """Advisor/Committee: ≥10 chars and ≥2 words; drop OCR role junk."""
    if not name:
        return False
    if _ROLE_JUNK_TOKEN.search(name):
        return False
    words = [w for w in re.findall(r"[A-Za-zก-๙]+", name) if w]
    if len(name) < 10 or len(words) < 2:
        return False
    if not re.fullmatch(r"[A-Za-zก-๙][A-Za-zก-๙ .,'()&-]*", name):
        return False
    return True


def _looks_like_author_name(line: str) -> bool:
    line_clean = _strip_field_label(line.strip(" .:-"))
    if not line_clean:
        return False
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
                finalized
                for candidate in candidates
                for finalized in [_finalize_person_name(candidate)]
                if _is_valid_supervisory_name(finalized)
                and not any(w.lower() in _TITLE_WORDS for w in re.findall(r"[A-Za-z]+", finalized or ""))
            ),
            None,
        )
        if name and name != advisor:
            if label.group(1).upper() in ("ADVISOR", "ADVISER"):
                advisor = name
            else:
                committee.append(name)

    return advisor, committee


def _extract_supervisory_block(lines: list[str]) -> tuple[str | None, list[str]]:
    """Parse Supervisory Advisor/Committee lines; keep roles clearly separated."""
    start = next(
        (index for index, line in enumerate(lines) if re.search(r"\bSupervisory\b", line, re.IGNORECASE)),
        None,
    )
    if start is None:
        return None, []

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _SUPERVISORY_STOP.match(lines[index]):
            end = index
            break

    advisor: str | None = None
    committee: list[str] = []

    for line in lines[start:end]:
        working = re.sub(
            r"^(?:Supervisory(?:\s+Committee)?|Committee)\s*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if not working:
            continue

        role_match = re.search(r"\s+(Advisor|Adviser|Committee)\s*$", working, re.IGNORECASE)
        if not role_match:
            continue

        name = _finalize_person_name(working[: role_match.start()])
        if not _is_valid_supervisory_name(name) or name == advisor:
            continue

        role = role_match.group(1).upper()
        if role in ("ADVISOR", "ADVISER"):
            if advisor is None:
                advisor = name
        else:
            committee.append(name)

    return advisor, list(dict.fromkeys(committee))


def _extract_keywords(lines: list[str]) -> str | None:
    """Read a Keywords or คำสำคัญ line. Values may sit on that line or the next one."""
    for index, line in enumerate(lines):
        match = _KEYWORD_LABEL.match(line)
        if not match:
            continue
        chunks = [match.group(1).strip(" .:-")]
        if not chunks[0]:
            for follow in lines[index + 1 : index + 3]:
                if _KEYWORD_STOP.match(follow):
                    break
                chunks.append(follow.strip(" .:-"))
        raw = " ".join(part for part in chunks if part)
        raw = _KEYWORD_STOP.split(raw, maxsplit=1)[0]
        items = [
            item.strip(" .;")
            for item in re.split(r"[,،;|/、]", raw)
            if item.strip(" .;")
        ]
        if len(items) == 1 and len(items[0]) > 80:
            return None
        if not items:
            continue
        unique = list(dict.fromkeys(items))[:15]
        return ", ".join(unique)
    return None


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
    }

    # Skip front-matter pages that should not extract titles/authors (e.g. acknowledgements, table of contents)
    header_check = first_page_text[:300].strip()
    if re.search(r"\b(?:ACKNOWLEDGEMENTS?|TABLE\s+OF\s+CONTENTS|กิตติกรรมประกาศ|สารบัญ)\b", header_check, re.IGNORECASE):
        return metadata

    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    metadata["keywords"] = _extract_keywords(lines)

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
            ca = _finalize_person_name(a)
            if _is_valid_author_name(ca) and ca not in cleaned_authors:
                cleaned_authors.append(ca)

        if cleaned_authors:
            metadata["author"] = ", ".join(cleaned_authors)

    # --- 3. Advisor and Committee (roles stay separated) ---
    found_advisor, found_committee = _extract_supervisory_block(lines)

    # Approval-page fallback only on EXAMINING COMMITTEE pages (avoid OCR junk
    # from broken Supervisory metadata pages being treated as labelled roles).
    if (found_advisor is None or not found_committee) and re.search(
        r"\bEXAMINING\s+COMMITTEE\b", first_page_text, re.IGNORECASE
    ):
        approval_advisor, approval_committee = _extract_approval_committee(lines)
        if found_advisor is None and approval_advisor:
            found_advisor = approval_advisor
        if not found_committee and approval_committee:
            found_committee = approval_committee

    cleaned_advisor = _finalize_person_name(found_advisor)
    metadata["advisor"] = cleaned_advisor if _is_valid_supervisory_name(cleaned_advisor) else None
    if found_committee:
        cleaned_committee_list = [
            name
            for raw in found_committee
            for name in [_finalize_person_name(raw)]
            if _is_valid_supervisory_name(name) and name != metadata["advisor"]
        ]
        if cleaned_committee_list:
            metadata["committee"] = ", ".join(dict.fromkeys(cleaned_committee_list))

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

    return metadata
