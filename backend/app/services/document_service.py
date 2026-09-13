import os
import shutil
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import ProcessingStatus

UPLOAD_DIR = "storage/documents"

def process_document_upload(
    db: Session,
    file: UploadFile,
    project_title: str,
    academic_year: int | None = None,
    advisor: str | None = None,
    authors: str | None = None,
    supervisory_committee: str | None = None
) -> Document:
    """
    Sprint 2 Core Logic:
    1. ตรวจสอบ project_title ซ้ำใน PostgreSQL (ถ้าซ้ำให้ลบ Project และ Document เก่าทิ้ง)
    2. จัดเก็บไฟล์ PDF ลงใน Local Storage
    3. บันทึกข้อมูลลง PostgreSQL และสั่ง Trigger AI Ingestion Pipeline (PDF Scan -> Chunk -> Embed Qdrant)
    """
    # 1. ตรวจสอบและลบโครงงานเดิมหากมีชื่อ project_title ซ้ำกัน
    existing_project = db.query(Project).filter(Project.title == project_title).first()
    if existing_project:
        for doc in existing_project.documents:
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except OSError:
                    pass
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

    # 3. บันทึกไฟล์ PDF ลง Local Disk Storage
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = file.filename.replace(" ", "_") if file.filename else "uploaded.pdf"
    file_path = os.path.join(UPLOAD_DIR, f"{project.id}_{safe_filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 4. สร้าง Record ในตาราง documents (สถานะเริ่มต้น PROCESSING)
    document = Document(
        project_id=project.id,
        filename=file.filename or "uploaded.pdf",
        file_path=file_path,
        title=project_title,
        supervisory_committee=supervisory_committee,
        status=ProcessingStatus.PROCESSING.value
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # 5. Trigger AI Ingestion Pipeline (pdf_scanning -> text_processor -> vector_store)
    try:
        from app.rag.embedding.pdf_scanning import scan_pdf_document
        from app.rag.embedding.text_processor import chunk_extracted_data
        from app.rag.embedding.vector_store import upload_to_qdrant

        pages = scan_pdf_document(file_path)
        chunks = chunk_extracted_data(pages)
        success = upload_to_qdrant(chunks)

        if success:
            document.status = ProcessingStatus.COMPLETED.value
        else:
            document.status = ProcessingStatus.FAILED.value
    except Exception:
        document.status = ProcessingStatus.FAILED.value

    db.commit()
    db.refresh(document)
    return document

def get_all_documents(db: Session, skip: int = 0, limit: int = 50) -> list[Document]:
    """
    ดึงรายการเอกสารทั้งหมดเรียงตามวันอัปโหลดล่าสุด
    """
    return db.query(Document).order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()

def get_document_by_id(db: Session, document_id: int) -> Document | None:
    """
    ค้นหาเอกสารตาม document_id
    """
    return db.query(Document).filter(Document.id == document_id).first()

def delete_document_by_id(db: Session, document_id: int) -> bool:
    """
    ลบเอกสารออกจาก PostgreSQL และ Local Disk Storage
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return False

    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError:
            pass

    project = document.project
    db.delete(document)

    if project and len(project.documents) == 0:
        db.delete(project)

    db.commit()
    return True