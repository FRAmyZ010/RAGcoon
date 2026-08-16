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
            title_limit = 2
            title = " ".join(lines[:title_limit])
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

    # --- 3. Advisor (Dictionary + Supervisory Committee Logic) ---
    advisor_map = {
        "Mahamah": "Dr. Mahamah Sebakor",
        "Surapol": "Aj. Surapol Vorapatratorn",
        "Tossapon": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
        "Natthakan": "Asst.Prof.Dr.Natthakan Iam-On",
        "Suppakarn": "Asst.Prof.Suppakarn Chansareewittaya",
        "Worasak": "Asst.Prof. Worasak Rueangsirarak",
        "Paweena Suebsombut,": "Paweena Suebsombut",
        "Kemachart Kemavuthanon":"Kemachart Kemavuthanon",
        "Khwunta Kirimasthong":"Asst.Prof. Khwunta Kirimasthong",
        "Pattaramon":"Asst.Prof. Pattaramon Vuttipittayamongkol",
        "Shanmugam":"Prof. Shanmugam Nandagopalan",
        
    }

    found_advisor = None
    for i, line in enumerate(lines):
        # ปรับให้หาคำว่า Supervisory ก็พอ เผื่อ Committee มันกระเด็นไปบรรทัดอื่น
        if re.search(r"Supervisory", line, re.IGNORECASE):
            # ตรวจสอบบรรทัดปัจจุบัน และ 2 บรรทัดถัดไป
            search_scope = lines[i : i + 3]
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
            mid_match = re.search(r"(?i)Supervisory\s+Committee\s+(.*?)\s+Advisor", combined_context)

            if mid_match:
                # ดึงข้อความที่อยู่ตรงกลางระหว่างคำว่า Committee กับ Advisor
                found_advisor = mid_match.group(1).strip()
                # ทำความสะอาดเศษอักขระที่อาจติดมาจากการสแกน เช่น จุด หรือ เครื่องหมายลบ
                found_advisor = found_advisor.strip(' .:-')
                break

    metadata["advisor"] = found_advisor

    # --- ส่วน Keywords (Logic ใหม่: สแกนทีละบรรทัด) ---
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    found_keywords = []
    start_collecting = False

    for i, line in enumerate(lines):
        # 1. หาบรรทัดที่มีคำว่า Keyword (รองรับตัวหนา/พิมพ์เล็ก-ใหญ่/มีหรือไม่มี s)
        if re.search(r"(?i)\bKeywords?\b", line):
            start_collecting = True
            # ลองดึงข้อมูลที่อาจจะอยู่ในบรรทัดเดียวกันมาด้วย (หลังเครื่องหมาย :)
            content_after_header = re.sub(r"(?i)Keywords?\s*[:\-]?\s*", "", line).strip()
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