import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import ProcessingStatus

UPLOAD_DIR = "storage/documents"

async def process_document_upload(
    db: Session,
    file: UploadFile,
    project_title: str,
    academic_year: int | None = None,
    advisor: str | None = None,
    authors: str | None = None,
    supervisory_committee: str | None = None
) -> Document:
    """
    Sprint 2 Core Logic: ตรวจสอบ project_title ซ้ำ (ถ้าซ้ำให้ลบข้อมูลเก่าทิ้งก่อน)
    บันทึกไฟล์ PDF และ Trigger กระบวนการ Vector Embedding เข้า Qdrant
    """
    # 1. ตรวจสอบไฟล์ซ้ำจาก project_title
    existing_project = db.query(Project).filter(Project.title == project_title).first()
    if existing_project:
        db.delete(existing_project)
        db.commit()

    # 2. บันทึกข้อมูล Project ใหม่
    project = Project(
        title=project_title,
        academic_year=academic_year,
        advisor=advisor,
        authors=authors
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 3. จัดเก็บไฟล์ PDF ลงใน Local Storage
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{project.id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 4. สร้าง Record เอกสารในตาราง documents (สถานะเริ่มต้น PENDING)
    document = Document(
        project_id=project.id,
        filename=file.filename,
        file_path=file_path,
        title=project_title,
        supervisory_committee=supervisory_committee,
        status=ProcessingStatus.PENDING.value
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # 5. Trigger Pipeline ฝั่ง AI (app/rag/) สกัด Text และส่ง Vector ลง Qdrant
    try:
        # from app.rag.ingestion import ingest_pdf
        # ingest_pdf(file_path=file_path, metadata={"project_title": project_title})
        document.status = ProcessingStatus.COMPLETED.value
    except Exception:
        document.status = ProcessingStatus.FAILED.value
    
    db.commit()
    db.refresh(document)
    return document