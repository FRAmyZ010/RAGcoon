from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from app.core.database import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    process_document_upload,
    get_all_documents,
    get_document_by_id,
    delete_document_by_id,
)

router = APIRouter(prefix="/documents", tags=["Document Ingestion & Management"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    project_title: str = Form(...),
    academic_year: int | None = Form(None),
    advisor: str | None = Form(None),
    authors: str | None = Form(None),
    supervisory_committee: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับอัปโหลดไฟล์ PDF + Metadata (สำหรับ Administrator)
    ระบบจะทำการสกัด Text, Chunking และ Embed ลง Qdrant Vector Database อัตโนมัติ
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รองรับเฉพาะไฟล์เอกสารประเภท PDF เท่านั้น"
        )

    try:
        return await run_in_threadpool(
            process_document_upload,
            db=db,
            file=file,
            project_title=project_title,
            academic_year=academic_year,
            advisor=advisor,
            authors=authors,
            supervisory_committee=supervisory_committee
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document Ingestion Error: {str(e)}"
        )

@router.get("", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Endpoint ดึงรายการเอกสารทั้งหมด พร้อมติดตามสถานะการประมวลผล (COMPLETED, PROCESSING, FAILED)
    """
    return get_all_documents(db=db, skip=skip, limit=limit)

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint ดึงรายละเอียดเอกสารรายชิ้นตาม ID
    """
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
    """
    Endpoint สำหรับลบเอกสารออกจากระบบ (PostgreSQL + Physical File)
    """
    success = delete_document_by_id(db=db, document_id=document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบเอกสารรหัส: {document_id}"
        )
    return {"message": f"ลบเอกสารรหัส {document_id} สำเร็จเรียบร้อยแล้ว"}