from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from app.core.database import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    process_document_upload_auto,
    get_all_documents,
    get_document_by_id,
    delete_document_by_id,
    resolve_document_file_path,
    DocumentUploadError,
)

router = APIRouter(prefix="/documents", tags=["Document Ingestion & Management"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับอัปโหลดไฟล์ PDF (Automated Flow)
    ผู้ใช้ส่งเพียงไฟล์ PDF เข้ามา ระบบจะทำการสกัด Metadata (Title, Author, Advisor, Year)
    พร้อมทำ Chunking และ Embed ลง Qdrant ให้อัตโนมัติ 100%
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น"
        )

    try:
        return await run_in_threadpool(
            process_document_upload_auto,
            db=db,
            file=file
        )
    except DocumentUploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document Auto-Ingestion Error: {str(e)}"
        )

@router.get("", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return get_all_documents(db=db, skip=skip, limit=limit)

@router.get("/{document_id}/file")
def download_document_file(
    document_id: int,
    download: bool = False,
    db: Session = Depends(get_db)
):
    """Serve the original PDF for browser preview / download."""
    file_path, filename = resolve_document_file_path(db=db, document_id=document_id)
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
    db: Session = Depends(get_db)
):
    success = delete_document_by_id(db=db, document_id=document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบเอกสารรหัส: {document_id}"
        )
    return {"message": f"ลบเอกสารรหัส {document_id} สำเร็จเรียบร้อยแล้ว"}
