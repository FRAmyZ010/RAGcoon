import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import ProcessingStatus

UPLOAD_DIR = "storage/documents"

def process_document_upload_auto(
    db: Session,
    file: UploadFile
) -> Document:
    """
    Automated Ingestion Flow:
    1. จัดเก็บไฟล์ PDF ชั่วคราวลง Disk Storage
    2. เรียก RAG Pipeline เพื่อสกัด Metadata (Title, Advisor, Author, Year) จากตัวไฟล์โดยอัตโนมัติ
    3. เช็ค Duplicate ใน PostgreSQL ผ่าน project_title ที่สกัดได้
    4. บันทึกข้อมูลลง PostgreSQL และ Vector Store (Qdrant)
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # 1. บันทึกไฟล์ PDF ชั่วคราวเข้า Storage เพื่อให้ RAG Engine อ่านได้
    safe_filename = file.filename.replace(" ", "_") if file.filename else "uploaded.pdf"
    temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{safe_filename}")

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Trigger AI Pipeline เพื่อสกัด Metadata จาก PDF 5 หน้าแรก
    try:
        from app.rag.embedding.pdf_scanning import scan_pdf_document
        from app.rag.embedding.text_processor import chunk_extracted_data
        from app.rag.embedding.vector_store import upload_to_qdrant

        pages = scan_pdf_document(temp_file_path)
        if not pages:
            raise ValueError("ไม่พบข้อความในไฟล์ PDF หรือไฟล์ชำรุด")

        # ดึง Metadata ที่ RAG Engine สกัดได้จากหน้าแรก
        extracted_meta = pages[0].get("metadata", {})
        project_title = extracted_meta.get("project_title") or file.filename or "Untitled Project"
        academic_year = int(extracted_meta["year"]) if extracted_meta.get("year") and str(extracted_meta["year"]).isdigit() else None
        advisor = extracted_meta.get("advisor")
        authors = extracted_meta.get("author")
        supervisory_committee = extracted_meta.get("committee")
        if isinstance(supervisory_committee, list):
            supervisory_committee = ", ".join(str(item) for item in supervisory_committee if item)
        keywords = extracted_meta.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(str(item) for item in keywords if item)

        # 3. ตรวจสอบโครงงานซ้ำ (Duplicate Check) จาก project_title ที่สกัดได้
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

        # 4. บันทึก Record ในตาราง projects
        project = Project(
            title=project_title,
            academic_year=academic_year,
            advisor=advisor,
            authors=authors
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # 5. เปลี่ยนชื่อและย้ายไฟล์ไปยัง Path จริงประจำ Project ID
        final_file_path = os.path.join(UPLOAD_DIR, f"{project.id}_{safe_filename}")
        if os.path.exists(temp_file_path):
            os.rename(temp_file_path, final_file_path)

        # 6. บันทึก Record ในตาราง documents
        document = Document(
            project_id=project.id,
            filename=file.filename or "uploaded.pdf",
            file_path=final_file_path,
            title=project_title,
            supervisory_committee=supervisory_committee,
            keywords=keywords,
            status=ProcessingStatus.PROCESSING.value
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # 7. ทำการ Chunking และ Upload Vector Embeddings เข้า Qdrant
        chunks = chunk_extracted_data(pages)
        success = upload_to_qdrant(chunks)

        document.status = ProcessingStatus.COMPLETED.value if success else ProcessingStatus.FAILED.value

    except Exception as e:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        raise e

    db.commit()
    db.refresh(document)
    return document

def get_all_documents(db: Session, skip: int = 0, limit: int = 50) -> list[Document]:
    return (
        db.query(Document)
        .options(joinedload(Document.project))
        .order_by(Document.upload_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_document_by_id(db: Session, document_id: int) -> Document | None:
    return (
        db.query(Document)
        .options(joinedload(Document.project))
        .filter(Document.id == document_id)
        .first()
    )

def delete_document_by_id(db: Session, document_id: int) -> bool:
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