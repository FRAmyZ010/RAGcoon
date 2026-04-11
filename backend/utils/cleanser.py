# utils/cleanser.py
import re

def clean_text(text):
    if not text:
        return ""

    # 1. เปลี่ยนการขึ้นบรรทัดใหม่ (\n) ให้เป็นช่องว่าง เพื่อให้ประโยคต่อกัน
    # แต่ต้องระวังไม่ให้คำติดกันเกินไป
    text = text.replace('\n', ' ')

    # 2. ลบช่องว่างที่ซ้ำซ้อน (Multiple spaces) ให้เหลือช่องเดียว
    text = re.sub(r'\s+', ' ', text)

    # 3. ลบตัวอักษรที่เป็น Noise (เช่น อักขระพิเศษแปลกๆ ที่ไม่ใช่ภาษาอังกฤษ/ตัวเลข/เครื่องหมายวรรคตอนพื้นฐาน)
    # หมายเหตุ: หากงานของคุณมีสูตรคณิตศาสตร์ อาจจะต้องปรับส่วนนี้
    text = re.sub(r'[^\x00-\x7F]+', ' ', text) # ลบ non-ASCII characters

    return text.strip()