from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

"""
ไฟล์สำหรับรับ-ส่งข้อมูล API และกำหนด Enum สถานะการทำงาน

Document Pydantic Schemas (Data Validation & Serialization Layer)

ไฟล์นี้ทำหน้าที่เป็น Data Transfer Object (DTO) สำหรับจัดการโครงสร้างข้อมูลของเอกสาร:
1. ProcessingStatus (Enum): กำหนดสถานะที่เป็นไปได้ของกระบวนการประมวลผล (PENDING, PROCESSING, COMPLETED, FAILED)
2. DocumentBase: Schema แม่แบบ เก็บฟิลด์ข้อมูลพื้นฐานที่ใช้ร่วมกัน
3. DocumentCreate: สำหรับ Validate ข้อมูลฝั่ง Request ขาเข้า ตอนอัปโหลด/สร้างเอกสารใหม่
4. DocumentUpdate: สำหรับ Validate ข้อมูลฝั่ง Request ขาเข้า ตอนอัปเดตข้อมูล/สถานะ (Partial Update)
5. DocumentResponse: สำหรับ Format ข้อมูลฝั่ง Response ขาออก โดยแปลง SQLAlchemy Model เป็น JSON ส่งกลับให้ Client
"""

class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentBase(BaseModel):
    filename: str
    title: Optional[str] = None
    supervisory_committee: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    supervisory_committee: Optional[str] = None
    status: Optional[ProcessingStatus] = None
    error_message: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    status: ProcessingStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)