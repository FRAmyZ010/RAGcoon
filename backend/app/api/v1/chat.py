from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from app.core.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SearchQueryHistoryResponse,
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
)
from app.services.rag_services import (
    process_rag_query,
    process_rag_stream,
    get_chat_history,
    get_all_workspaces,
    get_workspace_detail,
)

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])

@router.post("/query", response_model=ChatResponse)
async def query_rag(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับยิงคำถาม RAG แบบ Blocking (JSON Response) และบันทึกผลลัพธ์ลง PostgreSQL
    """
    try:
        return await run_in_threadpool(
            process_rag_query,
            db=db,
            query_text=request.query_text,
            workspace_id=request.workspace_id,
            parent_query_id=request.parent_query_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG Processing Error: {str(e)}"
        )

@router.post("/query-stream")
def query_rag_stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    SSE Endpoint สำหรับสตรีมมิ่งคำตอบแบบ Real-time (Server-Sent Events)
    """
    return StreamingResponse(
        process_rag_stream(
            db=db,
            query_text=request.query_text,
            workspace_id=request.workspace_id,
            parent_query_id=request.parent_query_id
        ),
        media_type="text/event-stream"
    )

@router.get("/workspaces", response_model=list[WorkspaceSummaryResponse])
def read_workspaces(
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับดึงรายการ Workspace ทั้งหมดสำหรับแสดงบน Sidebar
    """
    return get_all_workspaces(db=db)

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
def read_workspace_detail(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับดึงประวัติการค้นหาทั้งหมดใน Workspace ที่ระบุ
    """
    workspace_detail = get_workspace_detail(db=db, workspace_id=workspace_id)
    if not workspace_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบข้อมูล Workspace รหัส: {workspace_id}"
        )
    return workspace_detail

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