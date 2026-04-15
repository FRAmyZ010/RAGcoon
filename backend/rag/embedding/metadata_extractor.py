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

    # 1. Project Title: ดึง 1-2 บรรทัดแรก (ตัดช่องว่างที่อาจเกิดขึ้น)
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    if len(lines) >= 2:
        metadata["project_title"] = f"{lines[0]} {lines[1]}".strip()
    elif len(lines) == 1:
        metadata["project_title"] = lines[0]

    # 2. Author: หา Mr., Ms., หรือ Miss (Case-insensitive)
    author_match = re.search(r"(?i)(Mr\.|Ms\.|Miss)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", first_page_text)
    if author_match:
        metadata["author"] = author_match.group(0).strip()

    # 3. Advisor: หาบรรทัดที่มีคำว่า Advisor
    advisor_match = re.search(r"(.+?)\s+Advisor", first_page_text, re.IGNORECASE)
    if advisor_match:
        metadata["advisor"] = advisor_match.group(1).strip()

    # 4. Keywords: หา Keywords : แล้วเก็บค่าหลังจากนั้นจนจบประโยคหรือบรรทัด
    keywords_match = re.search(r"(?i)Keywords?\s*:\s*(.*)", first_page_text)
    if keywords_match:
        metadata["keywords"] = keywords_match.group(1).strip()

    # 5. Year: หาตัวเลข 4 หลักที่เป็น ค.ศ. (เช่น 2020-2029)
    # เรามักจะมองหาปีในช่วงปัจจุบันเพื่อความแม่นยำ
    year_match = re.search(r"\b(20[12]\d)\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group(1)

    return metadata