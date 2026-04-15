import re

def extract_project_metadata(first_page_text):
    """
    สกัดข้อมูลเฉพาะจากหน้าแรกของเอกสาร PDF โดยใช้ Regex
    """
    metadata = {
        "project_title": None,
        "author": None,
        "advisor": None,
        "keywords": None,
        "year": None
    }

    # แยกบรรทัดและลบช่องว่างหัวท้าย
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]

    if lines:
        # 1. Project Title: ดึง 1-2 บรรทัดแรกมารวมกัน
        if len(lines) >= 2:
            # รวมบรรทัดที่ 1 และ 2 เข้าด้วยกัน
            title = f"{lines[0]} {lines[1]}".strip()
        else:
            # ถ้ามีบรรทัดเดียว ก็เอาแค่บรรทัดแรก
            title = lines[0]

        # เช็คคำว่า (Project Proposal) เพิ่มเติมจากข้อความทั้งหมด
        proposal_match = re.search(r"\(Project\s+Proposal\)", first_page_text, re.IGNORECASE)
        if proposal_match:
            # ตรวจสอบก่อนว่าใน title ที่ดึงมามีคำนี้อยู่แล้วหรือยัง เพื่อไม่ให้ชื่อซ้ำซ้อน
            if proposal_match.group(0).lower() not in title.lower():
                title = f"{title} {proposal_match.group(0)}"
        
        metadata["project_title"] = title

    # 2. Author: หา Mr., Ms., หรือ Miss
    author_match = re.search(r"(?i)(Mr\.|Ms\.|Miss)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", first_page_text)
    if author_match:
        metadata["author"] = author_match.group(0).strip()

    # 3. Advisor: หาบรรทัดที่มีคำว่า Advisor
    advisor_match = re.search(r"(.+?)\s+Advisor", first_page_text, re.IGNORECASE)
    if advisor_match:
        metadata["advisor"] = advisor_match.group(1).strip()

    # 4. Keywords: หา Keywords :
    keywords_match = re.search(r"(?i)Keywords?\s*:\s*(.*)", first_page_text)
    if keywords_match:
        metadata["keywords"] = keywords_match.group(1).strip()

    # 5. Year: หา ค.ศ. 20xx
    year_match = re.search(r"\b(20[12]\d)\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group(1)

    return metadata