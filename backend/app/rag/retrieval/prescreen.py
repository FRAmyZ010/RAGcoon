"""
Module: prescreen.py
Description:
    RAGcoon Prescreen & Conversational Intent Engine
    - จัดการคำถามทักทาย (Greeting / INT-01)
    - จัดการคำถามสารทุกข์สุกดิบ / แนะนำตัว (Small Talk / Persona / INT-02)
    - จัดการคำถามกำกวมที่ไม่มีบริบท (Ambiguous / Clarification / INT-04)
    - จัดการคำถามนอกเรื่อง (Out of Domain / INT-05)
    - จัดการคำถามที่มีหลายเจตนา ทักทาย + คำถาม RAG (Mixed Intent / INT-06)
    - จัดการข้อความขยะ / สัญลักษณ์ (Nonsense / INT-07)
    - ตอบกลับทันทีในระดับมิลลิวินาที (Zero GPU / Zero Vector DB Overhead)
"""

import re
from dataclasses import dataclass
from typing import Optional

from .session_manager import session_manager


@dataclass
class PrescreenResult:
    handled: bool
    response: Optional[str] = None
    greeting_prefix: Optional[str] = None
    cleaned_query: str = ""
    intent: str = "NORMAL"


# 1. Nonsense Patterns (INT-07)
_NONSENSE_RE = re.compile(
    r"^(?:[\?\.\,\!\s\-\_\/\\~@#$%^&*()+=|`'\";:<>\{\}\[\]]{2,}|[a-zA-Z]{5,}|[0-9]{6,})$"
)
_KEYBOARD_SMASH = {
    "asdfghjkl", "asdf", "qwerty", "qwertyuiop", "zxcvbnm", "zxcv", "ghjkl", "hjkl",
    "12345", "123456", "1234567890", "test", "testing", "aaa", "aaaa", "aaaaa",
}

# 2. Greeting Phrases (INT-01)
_PURE_GREETINGS = {
    "สวัสดี", "สวัสดีครับ", "สวัสดีค่ะ", "สวัสดีจ้า", "สวัสดีฮะ", "สวัสดีนะ",
    "ดีจ้า", "ดีครับ", "ดีค่ะ", "หวัดดี", "หวัดดีครับ", "หวัดดีค่ะ", "ฮัลโหล", "ฮาโหล",
    "hi", "hello", "hey", "hiya", "good morning", "good afternoon", "good evening",
    "สวัสดียามเช้า", "สวัสดียามบ่าย", "สวัสดียามเย็น",
}

# 3. Small Talk / Persona Patterns (INT-02)
_WHO_ARE_YOU_TRIGGERS = [
    "คุณคือใคร", "คุณเป็นใคร", "เธอคือใคร", "มึงคือใคร", "แกคือใคร", "คุณชื่ออะไร",
    "ชื่ออะไร", "ใครสร้างคุณ", "ใครพัฒนาคุณ", "ผู้สร้างคือใคร",
    "who are you", "what is your name", "who created you", "who made you",
]

_WHAT_CAN_YOU_DO_TRIGGERS = [
    "ทำอะไรได้บ้าง", "ช่วยอะไรได้บ้าง", "คุณทำอะไรได้บ้าง", "ระบบนี้ทำอะไรได้บ้าง",
    "ทำไรได้บ้าง", "ช่วยไรได้บ้าง", "มีฟีเจอร์อะไรบ้าง", "ใช้งานอย่างไร",
    "what can you do", "help", "how to use", "features",
]

_EAT_FOOD_TRIGGERS = [
    "กินข้าวหรือยัง", "ทานข้าวหรือยัง", "กินข้าวยัง", "ทานข้าวยัง", "กินไรยัง",
    "หิวข้าวไหม", "กินอะไรหรือยัง", "have you eaten", "did you eat",
]

_HOW_ARE_YOU_TRIGGERS = [
    "สบายดีไหม", "เป็นอย่างไรบ้าง", "เหนื่อยไหม", "how are you", "are you ok", "how are things",
]

_THANK_YOU_TRIGGERS = [
    "ขอบคุณ", "ขอบคุณครับ", "ขอบคุณค่ะ", "ขอบใจ", "ขอบใจจ้า", "ขอบคุณมาก", "ขอบคุณมากๆ",
    "thanks", "thank you", "thx", "ty",
]

# 4. Ambiguous Follow-ups without context (INT-04)
_AMBIGUOUS_TRIGGERS = [
    "อันนั้นทำยังไง", "อันนี้ทำยังไง", "แล้วทำยังไง", "ทำยังไง", "ทำอย่างไร",
    "ขอข้อมูลเพิ่มเติม", "ขอรายละเอียดเพิ่มเติม", "แล้วยังไงต่อ", "อันนั้นคืออะไร",
    "แล้วไงต่อ", "เล่าต่อ", "อธิบายต่อ", "ขอเพิ่มอีก",
    "tell me more", "more info", "how does that work", "what about that",
]

# 5. Out of Domain Topics (INT-05)
_COOKING_TRIGGERS = [
    "วิธีทำผัดไทย", "สูตรผัดไทย", "ทำผัดไทย", "วิธีทำต้มยำ", "สูตรอาหาร", "วิธีทำอาหาร",
    "ทำกับข้าว", "สอนทำกับข้าว", "สูตรกะเพรา", "วิธีทำไข่เจียว", "how to cook", "recipe",
]

_WEATHER_TRIGGERS = [
    "สภาพอากาศเชียงรายวันนี้", "สภาพอากาศเชียงราย", "สภาพอากาศวันนี้", "สภาพอากาศ",
    "เชียงรายฝนตกไหม", "พรุ่งนี้ฝนตกไหม", "อากาศวันนี้", "อากาศเป็นไง", "weather today",
]

_CREATIVE_TRIGGERS = [
    "แต่งกลอนให้หน่อย", "แต่งกลอน", "แต่งเพลงให้หน่อย", "แต่งเพลง", "เล่าเรื่องผี",
    "ร้องเพลงให้ฟัง", "ดูดวง", "ทำนายดวง", "ราศี", "เล่นมุกหน่อย", "เล่าเรื่องตลก",
]


def prescreen_query(query: str, session_id: Optional[str] = None) -> PrescreenResult:
    """
    ตรวจสอบและจำแนกเจตนาคำถามก่อนเข้าสู่กระบวนการ RAG
    - ส่งกลับคำตอบทันทีสำหรับคำถามทั่วไป / ทักทาย / นอกขอบเขต
    - จัดการ Mixed Intent สำหรับคำถามที่มีคำทักทายนำหน้า
    """
    if not query or not query.strip():
        return PrescreenResult(
            handled=True,
            response="กรุณาพิมพ์คำถามหรือหัวข้อโครงงานที่ต้องการค้นหาครับ",
            intent="EMPTY",
        )

    q = query.strip()
    q_low = q.lower()
    q_clean = re.sub(r"[^\w\s\u0e00-\u0e7f]", "", q_low).strip()

    # -------------------------------------------------------------------------
    # 1. INT-07: ข้อความขยะ / สัญลักษณ์ (Nonsense)
    # -------------------------------------------------------------------------
    if _NONSENSE_RE.match(q) or q_clean in _KEYBOARD_SMASH or (len(q) >= 6 and len(set(q_clean)) <= 2):
        # Allow technical short acronyms if valid (e.g. PLC, IoT, BLE, RFID, GPS)
        technical_acronyms = {"plc", "iot", "ble", "rfid", "gps", "lora", "mqtt", "wifi", "wlan", "api"}
        if q_clean not in technical_acronyms:
            return PrescreenResult(
                handled=True,
                response="ขออภัยครับ RAGcoon ไม่เข้าใจข้อความดังกล่าว กรุณาพิมพ์คำถามหรือหัวข้อโครงงานวิศวกรรมคอมพิวเตอร์ที่ต้องการค้นหาใหม่อีกครั้งครับ",
                intent="NONSENSE",
            )

    # -------------------------------------------------------------------------
    # 2. INT-01: ทักทายทั่วไป (Pure Greeting)
    # -------------------------------------------------------------------------
    if q_clean in _PURE_GREETINGS or q_low in _PURE_GREETINGS:
        return PrescreenResult(
            handled=True,
            response=(
                "สวัสดีครับ! ผมคือ **RAGcoon** ผู้ช่วยสืบค้นและตอบคำถามเกี่ยวกับเอกสารโครงงานวิศวกรรมคอมพิวเตอร์ "
                "(Computer Engineering Senior Projects) มหาวิทยาลัยแม่ฟ้าหลวงครับ 🦝\n\n"
                "ยินดีให้บริการครับ วันนี้มีโครงงาน เทคโนโลยี หรือหัวข้อไหนที่สนใจเป็นพิเศษไหมครับ?"
            ),
            intent="GREETING",
        )

    # -------------------------------------------------------------------------
    # 3. INT-02: ถามสารทุกข์สุกดิบ / แนะนำตัว (Small Talk & Persona)
    # -------------------------------------------------------------------------
    # 3.1 คุณคือใคร / ใครสร้างคุณ
    if any(k in q_low for k in _WHO_ARE_YOU_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ผมคือ **RAGcoon** ระบบ AI ผู้ช่วยสืบค้นเอกสารโครงงานปริญญานิพนธ์ (Senior Projects) "
                "สาขาวิชาวิศวกรรมคอมพิวเตอร์ สำนักวิชาเทคโนโลยีสารสนเทศประยุกต์ มหาวิทยาลัยแม่ฟ้าหลวงครับ 🦝\n\n"
                "หน้าที่ของผมคือช่วยให้นักศึกษาและอาจารย์สามารถสืบค้นข้อมูลเชิงลึก สเปกฮาร์ดแวร์ ซอฟต์แวร์ "
                "ขั้นตอนการทำงาน และข้อมูลทะเบียนของโครงงานได้อย่างสะดวกรวดเร็ว แม่นยำ และมีเลขหน้าอ้างอิงจากเล่มจริงครับ"
            ),
            intent="SMALL_TALK",
        )

    # 3.2 ทำอะไรได้บ้าง / ช่วยอะไรได้บ้าง
    if any(k in q_low for k in _WHAT_CAN_YOU_DO_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ผมคือ **RAGcoon** ผู้ช่วยอัจฉริยะสำหรับสืบค้นเอกสารโครงงานวิศวกรรมคอมพิวเตอร์ครับ ผมสามารถช่วยคุณได้ดังนี้ครับ:\n\n"
                "• 🔍 **ค้นหาเนื้อหาเชิงลึก**: สเปกฮาร์ดแวร์, เซนเซอร์, บอร์ดไมโครคอนโทรลเลอร์, โค้ด และขั้นตอนการทำงาน พร้อม Citation อ้างอิงเลขหน้าจริงจากเล่ม PDF\n"
                "• ⚡ **ค้นหาข้อมูลทะเบียน**: ขอรายชื่อโครงงานตามปีการศึกษา (เช่น ปี 63, ปี 65), อาจารย์ที่ปรึกษา หรือคณะกรรมการสอบ ได้ในเสี้ยววินาที\n"
                "• ⚖️ **เปรียบเทียบโครงงาน**: เปรียบเทียบความแตกต่าง จุดเด่น และเทคโนโลยีระหว่าง 2 โครงงาน\n"
                "• 💡 **แนะนำหัวข้อโครงงาน**: แนะนำไอเดียและโครงงานที่น่าสนใจเพื่อนำไปพัฒนาต่อยอด\n\n"
                "สามารถพิมพ์ชื่อโครงงาน เทคโนโลยี หรือคำถามที่ต้องการทราบเพื่อเริ่มต้นได้เลยครับ!"
            ),
            intent="SMALL_TALK",
        )

    # 3.3 กินข้าวหรือยัง
    if any(k in q_low for k in _EAT_FOOD_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ผมเป็น AI ผู้ช่วย RAGcoon ทานข้าวไม่ได้ครับ 😄 แต่พร้อมช่วยคุณสืบค้นข้อมูลโครงงานวิศวกรรมคอมพิวเตอร์อย่างเต็มที่เลยครับ! "
                "มีโครงงานไหนที่อยากให้ผมช่วยหาไหมครับ?"
            ),
            intent="SMALL_TALK",
        )

    # 3.4 สบายดีไหม / เหนื่อยไหม
    if any(k in q_low for k in _HOW_ARE_YOU_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ผมสบายดีและพร้อมลุยงานเต็มที่ครับ! ขอบคุณที่ถามนะครับ 😊 มีข้อมูลโครงงานวิศวกรรมคอมพิวเตอร์เรื่องไหนที่อยากให้ช่วยค้นหา บอกได้เลยครับ"
            ),
            intent="SMALL_TALK",
        )

    # 3.5 ขอบคุณ
    if any(k == q_clean or q_clean.startswith(k) for k in _THANK_YOU_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ยินดีเป็นอย่างยิ่งครับ! หากมีข้อสงสัยหรือต้องการค้นหาข้อมูลโครงงานเพิ่มเติม "
                "สามารถสอบถาม RAGcoon ได้ตลอดเวลาเลยนะครับ ยินดีช่วยเหลือเสมอครับ 😊"
            ),
            intent="SMALL_TALK",
        )

    # -------------------------------------------------------------------------
    # 4. INT-04: คำถามกำกวมที่ไม่มีบริบทชี้เฉพาะ (Ambiguous Follow-up)
    # -------------------------------------------------------------------------
    is_ambiguous = any(k in q_clean for k in _AMBIGUOUS_TRIGGERS) or q_clean in _AMBIGUOUS_TRIGGERS
    if is_ambiguous:
        # Check if chat history has an active project context
        has_active_context = False
        if session_id:
            history = session_manager.get_history(session_id)
            if history and len(history) >= 2:
                has_active_context = True

        if not has_active_context:
            return PrescreenResult(
                handled=True,
                response=(
                    "ขออภัยครับ ไม่แน่ใจว่าคุณหมายถึงโครงงานหรือระบบไหนครับ? 🤔\n\n"
                    "กรุณาระบุ **ชื่อโครงงาน**, **เทคโนโลยี**, หรือ **หัวข้อที่ต้องการทราบเพิ่มเติม** ได้เลยครับ "
                    "เพื่อให้ RAGcoon ค้นหาข้อมูลที่ถูกต้องและตรงจุดที่สุดมาให้ครับ"
                ),
                intent="AMBIGUOUS",
            )

    # -------------------------------------------------------------------------
    # 5. INT-05: คำถามนอกขอบเขตระบบ (Out of Domain)
    # -------------------------------------------------------------------------
    if any(k in q_low for k in _COOKING_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ขออภัยด้วยครับ RAGcoon เป็นระบบ AI ที่เชี่ยวชาญเฉพาะการสืบค้นและตอบคำถามเกี่ยวกับ **เอกสารโครงงานวิศวกรรมคอมพิวเตอร์** เท่านั้นครับ 🍳\n\n"
                "จึงไม่สามารถตอบคำถามหรือให้สูตรอาหารได้ครับ หากมีคำถามเกี่ยวกับโครงงาน ฮาร์ดแวร์ หรือซอฟต์แวร์ สอบถามผมได้เลยนะครับ!"
            ),
            intent="OUT_OF_DOMAIN",
        )

    if any(k in q_low for k in _WEATHER_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ขออภัยด้วยครับ RAGcoon เป็นระบบ AI สำหรับสืบค้น **โครงงานวิศวกรรมคอมพิวเตอร์** จึงไม่มีการเชื่อมต่อข้อมูลสภาพอากาศแบบ Real-time ครับ ☀️🌧️\n\n"
                "แต่ถ้าต้องการค้นหาโครงงานเกี่ยวกับ *ระบบตรวจวัดสภาพอากาศด้วย IoT หรือสถานีอุตุนิยมวิทยา* สามารถบอกผมให้ค้นหาได้เลยครับ!"
            ),
            intent="OUT_OF_DOMAIN",
        )

    if any(k in q_low for k in _CREATIVE_TRIGGERS):
        return PrescreenResult(
            handled=True,
            response=(
                "ขออภัยด้วยครับ RAGcoon มุ่งเน้นการให้ข้อมูลและวิเคราะห์ทางเทคนิคเกี่ยวกับ **โครงงานวิศวกรรมคอมพิวเตอร์** เท่านั้นครับ 📝\n\n"
                "จึงไม่สามารถแต่งกลอน เล่าเรื่องผี หรือเล่นมุกได้ครับ หากมีคำถามเกี่ยวกับสเปกโครงงานหรือเนื้อหาทางเทคนิค สอบถามผมได้เลยนะครับ!"
            ),
            intent="OUT_OF_DOMAIN",
        )

    # -------------------------------------------------------------------------
    # 6. INT-06: คำถามที่มีหลายเจตนา ทักทาย + คำถาม RAG (Mixed Intent)
    # -------------------------------------------------------------------------
    # e.g. "สวัสดีจ้า ช่วยสรุปโปรเจค The LoRaWAN ให้หน่อย"
    greeting_prefix = None
    cleaned_query = query

    greeting_match = re.match(
        r"^(สวัสดีครับ|สวัสดีค่ะ|สวัสดีจ้า|สวัสดี|ดีจ้า|หวัดดีครับ|หวัดดีค่ะ|หวัดดี|hi|hello|hey)[\s,\.!]*",
        query,
        re.IGNORECASE,
    )
    if greeting_match:
        matched_greet = greeting_match.group(1).lower()
        remainder = query[greeting_match.end():].strip()
        if remainder:  # Has content after greeting
            cleaned_query = remainder
            if any(w in matched_greet for w in ["จ้า", "ดีจ้า"]):
                greeting_prefix = "สวัสดีจ้า! ยินดีช่วยเหลือครับ\n\n"
            else:
                greeting_prefix = "สวัสดีครับ! ยินดีช่วยเหลือครับ\n\n"

    return PrescreenResult(
        handled=False,
        greeting_prefix=greeting_prefix,
        cleaned_query=cleaned_query,
        intent="NORMAL",
    )
