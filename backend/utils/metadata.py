import os
import re

def extract_metadata(file_path, first_page_text, chunk_index):
    metadata = {
        "source": os.path.basename(file_path),
        "chunk_index": chunk_index,
        "project_title": "Unknown Title",
        "author": "Unknown Author",
        "advisor": "Unknown Advisor",
        "keywords": []
    }

    if not first_page_text:
        return metadata

    # แยกข้อความเป็นบรรทัด เพื่อไล่เช็คตาม Logic
    lines = [l.strip() for l in first_page_text.split('\n') if l.strip()]

    # 1. Logic: Title = 1-2 บรรทัดแรก
    if len(lines) >= 4:
        metadata["project_title"] = f"{lines[0]} {lines[1]}".strip()
    elif len(lines) == 1:
        metadata["project_title"] = lines[0]

    # แปลงกลับเป็นข้อความยาวเพื่อใช้ Regex ค้นหา Author/Advisor/Keyword
    full_text = "\n".join(lines)

    # 2. Logic: Author (เริ่มที่ 'Author' จบเมื่อเจอ 'Degree')
    # ใช้ re.DOTALL เพื่อให้ . รวมการขึ้นบรรทัดใหม่ด้วย
    author_block_match = re.search(r"Author\s+(.*?)(?=Degree|$)", full_text, re.IGNORECASE | re.DOTALL)
    if author_block_match:
        author_text = author_block_match.group(1).strip()
        # ทำความสะอาดช่องว่างเยอะๆ ให้เหลือบรรทัดเดียว หรือเก็บเป็น list ก็ได้
        metadata["author"] = re.sub(r'\s+', ' ', author_text)

    # 3. Logic: Advisor (ต้องมีคำว่า Advisor และมีคำนำหน้าชื่อ Asst, Prof, Dr.)
    # ดึงเฉพาะชื่อเดียวตามที่โจทย์กำหนด
    advisor_pattern = r".*Advisor.*(?:Asst|Prof|Dr\.)\s+[A-Za-z\s\.]+"
    advisor_match = re.search(advisor_pattern, full_text, re.IGNORECASE)
    if advisor_match:
        metadata["advisor"] = advisor_match.group(0).strip()

    # 4. Logic: Keyword (ตาม Format Keyword: A, B, C)
    keywords_match = re.search(r"Keyword\s*[:：]\s*([^\n]+)", full_text, re.IGNORECASE)
    if keywords_match:
        kw_str = keywords_match.group(1).strip()
        # แยกด้วย comma
        metadata["keywords"] = [k.strip() for k in re.split(r'[,]+', kw_str) if k]

    return metadata