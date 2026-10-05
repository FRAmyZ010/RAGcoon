import logging
import os
import shutil
import uuid
from typing import Any
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import ProcessingStatus

logger = logging.getLogger(__name__)

UPLOAD_DIR = "storage/documents"
# No per-file count cap; enforce total size at batch/API selection layer.
MAX_TOTAL_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB total per batch selection
MAX_TOTAL_UPLOAD_MB = MAX_TOTAL_UPLOAD_BYTES // (1024 * 1024)


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
    if size > MAX_TOTAL_UPLOAD_BYTES:
        raise DocumentUploadError(
            f"ขนาดไฟล์เกิน {MAX_TOTAL_UPLOAD_MB}MB "
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


def _safe_filename(filename: str | None) -> str:
    raw = filename.replace(" ", "_") if filename else "uploaded.pdf"
    return os.path.basename(raw) or "uploaded.pdf"


def accept_document_upload(db: Session, file: Any) -> Document:
    """
    Fast accept path:
    1. Save PDF to disk
    2. Validate size / PDF header / duplicate filename
    3. Insert Document row as PENDING
    4. Return immediately (ingest runs separately in background)
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

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

    safe_name = _safe_filename(file.filename)
    unique = uuid.uuid4().hex[:12]
    temp_file_path = os.path.join(UPLOAD_DIR, f"pending_{unique}_{safe_name}")

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        _assert_pdf_file(temp_file_path, file.filename)

        document = Document(
            project_id=None,
            filename=original_filename,
            file_path=temp_file_path,
            title=original_filename,
            status=ProcessingStatus.PENDING.value,
            status_message=None,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        final_file_path = os.path.join(UPLOAD_DIR, f"{document.id}_{safe_name}")
        if os.path.exists(temp_file_path):
            os.rename(temp_file_path, final_file_path)
        document.file_path = final_file_path
        db.commit()
        db.refresh(document)
        return document
    except DocumentUploadError:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        raise
    except Exception:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        raise


def ingest_document_by_id(db: Session, document_id: int) -> Document | None:
    """
    Background ingest for an accepted PENDING document:
    PENDING → PROCESSING → COMPLETED | FAILED
    """
    document = get_document_by_id(db=db, document_id=document_id)
    if not document:
        logger.warning("ingest skipped: document %s not found", document_id)
        return None

    if document.status not in (
        ProcessingStatus.PENDING.value,
        ProcessingStatus.PROCESSING.value,
    ):
        return document

    document.status = ProcessingStatus.PROCESSING.value
    document.status_message = None
    db.commit()
    db.refresh(document)

    file_path = document.file_path
    try:
        if not file_path or not os.path.exists(file_path):
            raise DocumentUploadError("ไม่พบไฟล์บนดิสก์สำหรับประมวลผล")

        from app.rag.embedding.pdf_scanning import scan_pdf_document
        from app.rag.embedding.text_processor import chunk_extracted_data
        from app.rag.embedding.vector_store import upload_to_qdrant

        pages = scan_pdf_document(file_path)
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
        project_title = (
            extracted_meta.get("project_title")
            or document.filename
            or "Untitled Project"
        )
        academic_year = (
            int(extracted_meta["year"])
            if extracted_meta.get("year") and str(extracted_meta["year"]).isdigit()
            else None
        )
        advisor = extracted_meta.get("advisor")
        authors = extracted_meta.get("author")
        supervisory_committee = extracted_meta.get("committee")
        if isinstance(supervisory_committee, list):
            supervisory_committee = ", ".join(
                str(item) for item in supervisory_committee if item
            )
        keywords = extracted_meta.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(str(item) for item in keywords if item)

        existing_project = (
            db.query(Project).filter(Project.title == project_title).first()
        )
        if existing_project and existing_project.id != document.project_id:
            raise DuplicateDocumentError(project_title)

        if document.project_id and document.project:
            project = document.project
            project.title = project_title
            project.academic_year = academic_year
            project.advisor = advisor
            project.authors = authors
            db.commit()
            db.refresh(project)
        else:
            project = Project(
                title=project_title,
                academic_year=academic_year,
                advisor=advisor,
                authors=authors,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

        for page in pages:
            page_meta = page.get("metadata")
            if isinstance(page_meta, dict):
                page_meta["source"] = os.path.basename(file_path)

        document.project_id = project.id
        document.title = project_title
        document.supervisory_committee = supervisory_committee
        document.keywords = keywords
        db.commit()

        chunks = chunk_extracted_data(pages)
        success = upload_to_qdrant(chunks)
        if success:
            document.status = ProcessingStatus.COMPLETED.value
            document.status_message = None
        else:
            document.status = ProcessingStatus.FAILED.value
            document.status_message = "อัปโหลดไปยัง vector store (Qdrant) ไม่สำเร็จ"
        db.commit()
        db.refresh(document)
        return document

    except DocumentUploadError as e:
        logger.warning("ingest failed for document %s: %s", document_id, e.message)
        db.rollback()
        document = get_document_by_id(db=db, document_id=document_id)
        if document:
            document.status = ProcessingStatus.FAILED.value
            document.status_message = e.message
            db.commit()
            db.refresh(document)
        return document
    except Exception as e:
        logger.exception("ingest error for document %s: %s", document_id, e)
        db.rollback()
        document = get_document_by_id(db=db, document_id=document_id)
        if document:
            document.status = ProcessingStatus.FAILED.value
            document.status_message = f"เกิดข้อผิดพลาดระหว่างประมวลผล: {e}"
            db.commit()
            db.refresh(document)
        return document


def ingest_document_task(document_id: int) -> None:
    """BackgroundTasks entrypoint — opens its own DB session."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        ingest_document_by_id(db=db, document_id=document_id)
    finally:
        db.close()


def process_document_upload_auto(
    db: Session,
    file: Any
) -> Document:
    """
    Synchronous accept + ingest (for callers that need a finished document).
    Prefer accept_document_upload + ingest_document_task for API uploads.
    """
    document = accept_document_upload(db=db, file=file)
    ingest_document_by_id(db=db, document_id=document.id)
    refreshed = get_document_by_id(db=db, document_id=document.id)
    return refreshed or document


def get_all_documents(db: Session, skip: int = 0, limit: int = 50) -> list[Document]:
    status_rank = case(
        (Document.status == ProcessingStatus.FAILED.value, 0),
        (Document.status == ProcessingStatus.COMPLETED.value, 1),
        (Document.status == ProcessingStatus.PROCESSING.value, 2),
        (Document.status == ProcessingStatus.PENDING.value, 3),
        else_=4,
    )
    return (
        db.query(Document)
        .options(joinedload(Document.project))
        .order_by(
            status_rank.asc(),
            Document.upload_date.desc(),
            Document.title.asc(),
            Document.filename.asc(),
        )
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


def record_document_view(db: Session, document_id: int) -> None:
    document = db.get(Document, document_id)
    if document is None:
        return
    document.view_count = (document.view_count or 0) + 1
    db.commit()


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
