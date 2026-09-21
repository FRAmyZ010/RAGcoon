from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, SearchQueryHistoryResponse
from app.services.rag_services import process_rag_query, get_chat_history

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])

@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_250_OK if hasattr(status, 'HTTP_250_OK') else 200)
def query_rag(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับยิงคำถาม RAG และบันทึกผลลัพธ์ลง PostgreSQL
    """
    try:
        return process_rag_query(
            db=db,
            query_text=request.query_text,
            parent_query_id=request.parent_query_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการประมวลผลคำถาม: {str(e)}"
        )

@router.get("/history", response_model=list[SearchQueryHistoryResponse])
def read_chat_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับดึงรายการประวัติการค้นหาย้อนหลัง
    """
    return get_chat_history(db=db, skip=skip, limit=limit)