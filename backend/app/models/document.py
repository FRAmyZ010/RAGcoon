from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from app.schemas.document import ProcessingStatus

"""
ไฟล์กำหนดโครงสร้างตารางใน PostgreSQL โดยใช้ SQLAlchemy (นำเข้า Base จาก app.core.database)

Document SQLAlchemy ORM Model (Database Layer)

ไฟล์นี้ทำหน้าที่เป็นตัวแทนตาราง 'documents' ใน PostgreSQL:
1. กำหนด Primary Key (document_id) และ Foreign Keys สำหรับเชื่อมกับตารางอื่น
2. จัดเก็บข้อมูลไฟล์เอกสาร (filename, file_path) และ Metadata ที่สแกนได้ (title, supervisory_committee, doc_metadata)
3. ติดตามสถานะกระบวนการ RAG Ingestion Pipeline (status, error_message)
4. บันทึกประวัติเวลาการอัปโหลดและการแก้ไข (uploaded_at, updated_at)
"""

class Document(Base):
    __tablename__ = "documents"

    # Primary Key
    document_id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    projects_id = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, nullable=True)

    # File Info
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)

    # Metadata & Extracted Info
    title = Column(String(500), nullable=True)
    supervisory_committee = Column(Text, nullable=True)
    doc_metadata = Column("metadata", JSON, nullable=True) # ฟิลด์ JSON สำหรับเก็บ RAG Filter Extra Metadata

    status = Column(String(50), default=ProcessingStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    uplaoded_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))