from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, DocumentCitation
from app.models.chat import SearchQuery

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"]
)

@router.post("/", response_model=ChatResponse)
def mock_chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Sprint 1: Mock API สำหรับรับคำถามและส่งคำตอบจำลองกลับไป
    โดยจะมีการบันทึก Request/Response สมมติลงในฐานข้อมูลตาราง `search_queries` จริง
    """
    # 1. รับคำถามและจำลองการตอบจาก RAG
    mock_response_text = f"นี่คือคำตอบจำลองจาก AI RAGcoon สำหรับคำถามที่คุณถามว่า: '{request.query_text}'"
    
    # 2. จำลองข้อมูลเอกสารอ้างอิง (Metadata)
    mock_citations = [
        DocumentCitation(
            document_id=1,
            title="The Development of Bluetooth Low Energy in Cisco WLAN",
            page=16,
            content="With the foundational aspects in place, we embarked on an ambitious endeavor...",
            score=2.8901
        ),
        DocumentCitation(
            document_id=1,
            title="The Development of Bluetooth Low Energy in Cisco WLAN",
            page=5,
            content="Title The development of Bluetooth low energy in cisco WLAN Author Mr.Kiattisak...",
            score=-0.9847
        )
    ]
    
    # แปลง List of Pydantic model ไปเป็น list of dict สำหรับเก็บลง JSON Column
    retrieved_docs_json = [citation.model_dump() for citation in mock_citations]
    
    # 3. สร้าง Record เพื่อบันทึกลง Database
    new_query = SearchQuery(
        user_id=request.user_id,
        parent_query_id=request.parent_query_id,
        query_text=request.query_text,
        response_text=mock_response_text,
        retrieved_docs=retrieved_docs_json
    )
    
    # 4. บันทึกและดึงข้อมูลอัปเดต (เช่น query_id และ created_at) จาก DB
    db.add(new_query)
    db.commit()
    db.refresh(new_query)
    
    # 5. ส่ง Response กลับไปให้ Frontend
    return ChatResponse(
        query_id=new_query.query_id,
        response_text=new_query.response_text,
        retrieved_docs=mock_citations,
        created_at=new_query.created_at
    )
