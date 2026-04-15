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

    # 1. นิยามกลุ่มคำที่เราต้องการค้นหา (คุณสามารถเพิ่มคำได้ที่นี่)
    tech_taxonomy = [
        "Machine Learning", "Deep Learning", "Artificial Intelligence",
        "Arduino", "ESP32", "Raspberry Pi", "IoT", "Internet of Things",
        "Sensor", "Node.js", "React", "FastAPI", "Python", "SQL", "PostgreSQL",
        "Mobile Application", "Web Application", "Image Processing",
        "Neural Network", "RAG", "LLM", "Llama"
    ]

    found_keywords = []

    # 2. ค้นหาคำจาก Taxonomy ในเนื้อหาหน้าแรก
    for tech in tech_taxonomy:
        # ใช้ \b เพื่อให้หาแบบเป็นคำ (เช่น หา 'RAG' จะไม่ไปติดในคำว่า 'DRAG')
        if re.search(rf"(?i)\b{re.escape(tech)}\b", first_page_text):
            found_keywords.append(tech)

    # 3. ลองใช้ Regex แบบเดิมเป็นทางเลือกสำรอง (ถ้าเผื่อสกัดคำแปลกๆ ออกมาได้)
    # ค้นหาช่วง Keywords: ... จนจบหน้าหรือเจอจุดตัด
    keywords_match = re.search(r"(?i)Keywords?\s*[:\-]?\s*([\s\S]+?)(?=\n\n|Year|\b20[12]\d\b|$)", first_page_text)
    
    if keywords_match:
        extracted_text = keywords_match.group(1).strip()
        # ถ้าสกัดออกมาได้ ให้ลองเอามาแยกด้วย comma แล้วเติมเข้าไป
        potential_kws = [k.strip() for k in re.split(r'[,;\n]', extracted_text) if len(k.strip()) > 2]
        for pk in potential_kws:
            if pk.lower() not in [f.lower() for f in found_keywords]:
                found_keywords.append(pk)

    # รวมผลลัพธ์
    if found_keywords:
        # ลบคำซ้ำและเชื่อมด้วย comma
        unique_kws = []
        [unique_kws.append(x) for x in found_keywords if x not in unique_kws]
        metadata["keywords"] = ", ".join(unique_kws[:10]) # เก็บสูงสุด 10 คำ
    # Year
    year_match = re.search(r"\b(20[12]\d)\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group(1)

    return metadata