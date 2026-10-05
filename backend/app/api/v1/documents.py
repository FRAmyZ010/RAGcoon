from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
import os
from app.api.deps import get_current_administrator
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    BatchUploadResponse,
    BatchUploadItemResult,
    BatchUploadSummary,
)
from app.services.document_service import (
    accept_document_upload,
    ingest_document_task,
    get_all_documents,
    get_document_by_id,
    delete_document_by_id,
    resolve_document_file_path,
    record_document_view,
    DocumentUploadError,
    MAX_TOTAL_UPLOAD_BYTES,
    MAX_TOTAL_UPLOAD_MB,
)

router = APIRouter(prefix="/documents", tags=["Document Ingestion & Management"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_administrator),
):
    """
    Accept a PDF quickly (PENDING), then ingest asynchronously.
    Status transitions: PENDING → PROCESSING → COMPLETED | FAILED.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น"
        )

    try:
        document = await run_in_threadpool(
            accept_document_upload,
            db=db,
            file=file,
        )
    except DocumentUploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document Accept Error: {str(e)}"
        )

    background_tasks.add_task(ingest_document_task, document.id)
    return document


@router.post(
    "/upload-batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_administrator),
):
    """
    Accept multiple PDFs in one request (total size ≤ MAX_TOTAL_UPLOAD_BYTES).
    Each accepted file is queued for async ingest. No max file-count cap.
    Partial success: accepted files return PENDING rows; rejected files return errors.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ต้องมีไฟล์อย่างน้อย 1 ไฟล์",
        )

    total_bytes = 0
    for file in files:
        # Best-effort size probe; full validation still runs per file on disk.
        try:
            pos = file.file.tell()
            file.file.seek(0, os.SEEK_END)
            total_bytes += file.file.tell()
            file.file.seek(pos)
        except Exception:
            pass

    if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"ขนาดไฟล์รวมเกิน {MAX_TOTAL_UPLOAD_MB}MB "
                f"(ขนาดปัจจุบัน {total_bytes / (1024 * 1024):.1f}MB)"
            ),
        )

    results: list[BatchUploadItemResult] = []
    accepted_ids: list[int] = []

    for file in files:
        filename = file.filename or "uploaded.pdf"

        if not file.filename or not file.filename.lower().endswith(".pdf"):
            results.append(
                BatchUploadItemResult(
                    filename=filename,
                    ok=False,
                    error="รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น",
                    status_code=400,
                )
            )
            continue

        try:
            document = await run_in_threadpool(
                accept_document_upload,
                db=db,
                file=file,
            )
            accepted_ids.append(document.id)
            results.append(
                BatchUploadItemResult(
                    filename=filename,
                    ok=True,
                    document=DocumentResponse.model_validate(document),
                    status_code=201,
                )
            )
        except DocumentUploadError as e:
            db.rollback()
            results.append(
                BatchUploadItemResult(
                    filename=filename,
                    ok=False,
                    error=e.message,
                    status_code=e.status_code,
                )
            )
        except Exception as e:
            db.rollback()
            results.append(
                BatchUploadItemResult(
                    filename=filename,
                    ok=False,
                    error=f"Document Accept Error: {str(e)}",
                    status_code=500,
                )
            )

    for document_id in accepted_ids:
        background_tasks.add_task(ingest_document_task, document_id)

    succeeded = sum(1 for item in results if item.ok)
    failed = len(results) - succeeded
    return BatchUploadResponse(
        results=results,
        summary=BatchUploadSummary(
            total=len(results),
            succeeded=succeeded,
            failed=failed,
        ),
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_administrator),
):
    return get_all_documents(db=db, skip=skip, limit=limit)

@router.get("/{document_id}/file")
def download_document_file(
    document_id: int,
    download: bool = False,
    db: Session = Depends(get_db)
):
    """Serve the original PDF for browser preview / download (Public)."""
    file_path, filename = resolve_document_file_path(db=db, document_id=document_id)
    if file_path:
        record_document_view(db=db, document_id=document_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบไฟล์เอกสารรหัส: {document_id}"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Document metadata by id (Public — used with citations / preview)."""
    doc = get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบเอกสารรหัส: {document_id}"
        )
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_administrator),
):
    success = delete_document_by_id(db=db, document_id=document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบเอกสารรหัส: {document_id}"
        )
    return {"message": f"ลบเอกสารรหัส {document_id} สำเร็จเรียบร้อยแล้ว"}
