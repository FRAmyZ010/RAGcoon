import re

def extract_project_metadata(first_page_text):
    metadata = {
        "project_title": None,
        "author": None,
        "advisor": None,
        "keywords": None,
        "year": None
    }

    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]

    if len(lines) >= 1:
        # --- Project Title ---
        title_limit = 1
        title = " ".join(lines[:title_limit])
        
        # แก้จุดที่ 1: ย้าย (?i) มาไว้หน้าสุด
        proposal_match = re.search(r"(?i)\(Project\s+Proposal\)", first_page_text)
        if proposal_match and proposal_match.group(0).lower() not in title.lower():
            title = f"{title} {proposal_match.group(0)}"
        
        metadata["project_title"] = title

        # --- Author ---
        authors = []
        potential_author_lines = lines[title_limit : title_limit + 8] 
        
        for line in potential_author_lines:
            # แก้จุดที่ 2: ใช้ re.IGNORECASE แทนการใส่ (?i) ใน string
            if re.search(r"Bachelor", line, re.IGNORECASE):
                break
            
            if re.search(r"Advisor|Keywords?|Year", line, re.IGNORECASE):
                break

            # รูปแบบชื่อตัวพิมพ์ใหญ่
            is_uppercase_name = re.match(r"^[A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})*$", line)
            # แก้จุดที่ 3: ย้าย (?i) มาหน้าสุดสำหรับ Prefix
            is_prefix_name = re.match(r"(?i)(Mr\.|Ms\.|Miss)\s+[A-Z].*", line)

            if is_uppercase_name or is_prefix_name:
                authors.append(line)
        
        if authors:
            metadata["author"] = ", ".join(authors)

    # --- ส่วนที่เหลือใช้ flags=re.IGNORECASE เพื่อความปลอดภัย ---
    # Advisor
    advisor_match = re.search(r"(.+?)\s+Advisor", first_page_text, re.IGNORECASE)
    if advisor_match:
        metadata["advisor"] = advisor_match.group(1).strip()

    # Keywords
    keywords_match = re.search(r"Keywords?\s*:\s*(.*)", first_page_text, re.IGNORECASE)
    if keywords_match:
        metadata["keywords"] = keywords_match.group(1).strip()

    # Year
    year_match = re.search(r"\b(20[12]\d)\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group(1)

    return metadata