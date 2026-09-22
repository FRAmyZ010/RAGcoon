import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import ProcessingStatus

UPLOAD_DIR = "storage/documents"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB per file
MAX_TOTAL_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB total per batch selection
MAX_BATCH_UPLOAD_FILES = 10


class DocumentUploadError(Exception):
    """Controlled upload validation error mapped to HTTP 4xx by the API layer."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DuplicateDocumentError(DocumentUploadError):
    def __init__(self, project_title: str):
        super().__init__(
            message=(
                f"พบเอกสารชื่อโครงงานซ้ำ: \"{project_title}\" "
                "กรุณาลบเอกสารเดิมก่อน หรืออัปโหลดไฟล์คนละโครงงาน"
            ),
            status_code=409,
        )
        self.project_title = project_title


def _assert_pdf_file(temp_file_path: str, filename: str | None) -> None:
    size = os.path.getsize(temp_file_path)
    if size <= 0:
        raise DocumentUploadError("ไฟล์ว่างเปล่า ไม่สามารถอัปโหลดได้")
    if size > MAX_UPLOAD_BYTES:
        raise DocumentUploadError(
            f"ไฟล์ใหญ่เกิน {MAX_UPLOAD_BYTES // (1024 * 1024)}MB "
            f"(ขนาดปัจจุบัน {size / (1024 * 1024):.1f}MB)"
        )

    with open(temp_file_path, "rb") as fh:
        header = fh.read(5)
    if not header.startswith(b"%PDF"):
        raise DocumentUploadError(
            "ไฟล์ไม่ใช่ PDF ที่ถูกต้อง หรือไฟล์เสียหาย (ต้องขึ้นต้นด้วย %PDF)"
        )

    if filename and not filename.lower().endswith(".pdf"):
        raise DocumentUploadError("รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น")


def process_document_upload_auto(
    db: Session,
    file: UploadFile
) -> Document:
    """
    Automated Ingestion Flow:
    1. จัดเก็บไฟล์ PDF ชั่วคราวลง Disk Storage
    2. ตรวจสอบขนาด / PDF header
    3. เรียก RAG Pipeline เพื่อสกัด Metadata
    4. ปฏิเสธถ้า project_title ซ้ำ (409)
    5. บันทึก PostgreSQL + Qdrant
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_filename = file.filename.replace(" ", "_") if file.filename else "uploaded.pdf"
    temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{safe_filename}")

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        _assert_pdf_file(temp_file_path, file.filename)

        original_filename = file.filename or "uploaded.pdf"
        existing_filename = (
            db.query(Document)
            .filter(Document.filename == original_filename)
            .first()
        )
        if existing_filename:
            raise DocumentUploadError(
                f'พบไฟล์ชื่อซ้ำ: "{original_filename}" '
                "กรุณาลบไฟล์เดิมก่อน หรือเปลี่ยนชื่อไฟล์",
                status_code=409,
            )

        from app.rag.embedding.pdf_scanning import scan_pdf_document
        from app.rag.embedding.text_processor import chunk_extracted_data
        from app.rag.embedding.vector_store import upload_to_qdrant

        pages = scan_pdf_document(temp_file_path)
        if not pages:
            raise DocumentUploadError("ไม่พบข้อความในไฟล์ PDF หรือไฟล์ชำรุด")

        has_text = any(
            isinstance(page.get("content"), str) and page["content"].strip()
            for page in pages
        )
        if not has_text:
            raise DocumentUploadError(
                "อ่านข้อความจาก PDF ไม่ได้ (อาจเป็นสแกนภาพอย่างเดียว หรือไฟล์เสีย)"
            )

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

        existing_project = db.query(Project).filter(Project.title == project_title).first()
        if existing_project:
            raise DuplicateDocumentError(project_title)

        project = Project(
            title=project_title,
            academic_year=academic_year,
            advisor=advisor,
            authors=authors
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        final_file_path = os.path.join(UPLOAD_DIR, f"{project.id}_{safe_filename}")
        if os.path.exists(temp_file_path):
            os.rename(temp_file_path, final_file_path)

        for page in pages:
            page_meta = page.get("metadata")
            if isinstance(page_meta, dict):
                page_meta["source"] = os.path.basename(final_file_path)

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

        chunks = chunk_extracted_data(pages)
        success = upload_to_qdrant(chunks)

        document.status = ProcessingStatus.COMPLETED.value if success else ProcessingStatus.FAILED.value

    except DocumentUploadError:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        raise
    except Exception as e:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        # Normalize common PDF parse failures to 400
        message = str(e)
        if any(token in message.lower() for token in ("pdf", "syntax", "decrypt", "trailer", "eof")):
            raise DocumentUploadError(f"ไฟล์ PDF เสียหรืออ่านไม่ได้: {message}") from e
        raise

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

def resolve_document_file_path(
    db: Session,
    document_id: int,
) -> tuple[str | None, str | None]:
    """Return (absolute_or_relative_path, download_filename) if the PDF exists on disk."""
    document = get_document_by_id(db=db, document_id=document_id)
    if not document or not document.file_path:
        return None, None
    if not os.path.exists(document.file_path):
        return None, None
    return document.file_path, document.filename or os.path.basename(document.file_path)

def find_document_for_citation(
    db: Session,
    *,
    source: str | None = None,
    project_title: str | None = None,
) -> Document | None:
    """Resolve a citation payload back to a Document row."""
    if source:
        source_name = os.path.basename(source.strip())
        if source_name:
            doc = (
                db.query(Document)
                .filter(
                    (Document.filename == source_name)
                    | (Document.file_path.endswith(source_name))
                )
                .order_by(Document.id.desc())
                .first()
            )
            if doc:
                return doc

            # Older uploads may have used temp_{filename} as Qdrant source
            if source_name.startswith("temp_"):
                original = source_name[len("temp_"):]
                doc = (
                    db.query(Document)
                    .filter(
                        (Document.filename == original)
                        | (Document.file_path.endswith(original))
                        | (Document.file_path.contains(f"_{original}"))
                    )
                    .order_by(Document.id.desc())
                    .first()
                )
                if doc:
                    return doc

    if project_title and project_title.strip():
        title = project_title.strip()
        doc = (
            db.query(Document)
            .filter(Document.title == title)
            .order_by(Document.id.desc())
            .first()
        )
        if doc:
            return doc

        project = db.query(Project).filter(Project.title == title).first()
        if project and project.documents:
            return max(project.documents, key=lambda d: d.id)

    return None

def enrich_citations_with_document_ids(
    db: Session,
    citations: list[dict] | None,
) -> list[dict]:
    """Attach document_id (and a single page) so the Chat UI can open PDF preview."""
    if not citations:
        return []

    enriched: list[dict] = []
    for raw in citations:
        citation = dict(raw) if isinstance(raw, dict) else {}
        source = citation.get("source")
        project_title = citation.get("project_title")
        document = find_document_for_citation(
            db,
            source=source,
            project_title=project_title,
        )
        if document:
            citation["document_id"] = document.id

        # Normalize page for frontend: prefer explicit page, else first of pages list
        if citation.get("page") is None:
            pages = citation.get("pages")
            if isinstance(pages, list) and pages:
                try:
                    citation["page"] = int(pages[0])
                except (TypeError, ValueError):
                    pass

        enriched.append(citation)

    return enriched

def _purge_document_row_and_orphan_project(db: Session, document: Document) -> None:
    """
    Remove the document row; if its Project has no documents left, remove Project too.

    Must flush before counting siblings — an unflushed delete still appears in
    relationship collections / queries and previously left orphan projects
    (unique title → 409 on re-upload).
    """
    project_id = document.project_id
    db.delete(document)
    db.flush()

    if project_id is None:
        return

    remaining = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .count()
    )
    if remaining == 0:
        orphan = db.get(Project, project_id)
        if orphan is not None:
            db.delete(orphan)


def delete_document_by_id(db: Session, document_id: int) -> bool:
    document = (
        db.query(Document)
        .options(joinedload(Document.project))
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        return False

    from app.rag.embedding.vector_store import delete_from_qdrant

    project_title = document.title
    if document.project and document.project.title:
        project_title = document.project.title

    # ลบ vectors ก่อน แล้วค่อยลบไฟล์/DB
    delete_from_qdrant(
        project_title=project_title,
        filename=document.filename,
        file_path=document.file_path,
    )

    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError:
            pass

    _purge_document_row_and_orphan_project(db, document)
    db.commit()
    return True
