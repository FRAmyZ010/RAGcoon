from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
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
    ChatModelError,
    process_rag_query,
    process_rag_stream,
    resolve_chat_config,
    get_chat_history,
    get_all_workspaces,
    get_workspace_detail,
)

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])

_recent_sends: dict[str, list[float]] = {}


def _too_many_sends(client_key: str, limit: int = 8, window_seconds: float = 10) -> bool:
    import time

    now = time.time()
    recent = [stamp for stamp in _recent_sends.get(client_key, []) if now - stamp < window_seconds]
    if len(recent) >= limit:
        _recent_sends[client_key] = recent
        return True
    recent.append(now)
    _recent_sends[client_key] = recent
    return False

@router.post("/query", response_model=ChatResponse)
async def query_rag(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint สำหรับยิงคำถาม RAG แบบ Blocking (JSON Response) และบันทึกผลลัพธ์ลง PostgreSQL
    """
    try:
        config = resolve_chat_config(db, request.llm_model, request.profile_name)
        return await run_in_threadpool(
            process_rag_query,
            db=db,
            query_text=request.query_text,
            workspace_id=request.workspace_id,
            parent_query_id=request.parent_query_id,
            messages=request.messages,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            config=config,
            config_resolved=True,
        )
    except ChatModelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG Processing Error: {str(e)}"
        )

@router.post("/query-stream")
def query_rag_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    SSE Endpoint สำหรับสตรีมมิ่งคำตอบแบบ Real-time (Server-Sent Events)
    """
    client_key = http_request.client.host if http_request.client else "unknown"
    if _too_many_sends(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Wait a moment and try again.",
        )
    try:
        config = resolve_chat_config(db, request.llm_model, request.profile_name)
    except ChatModelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return StreamingResponse(
        process_rag_stream(
            db=db,
            query_text=request.query_text,
            workspace_id=request.workspace_id,
            parent_query_id=request.parent_query_id,
            messages=request.messages,
            background_tasks=background_tasks,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            config=config,
            config_resolved=True,
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
            detail=f"Workspace not found: {workspace_id}"
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


@router.post("/compare")
async def compare_rag_pipelines(request: ChatRequest):
    """Compare the legacy pipeline with the current hybrid pipeline for one query."""
    from app.rag.evaluation.compare_pipelines import compare_query
    return await run_in_threadpool(compare_query, query=request.query_text)


@router.get("/benchmark-suite")
async def run_benchmark_endpoint():
    """Run the legacy-vs-modern benchmark scenarios."""
    from app.rag.evaluation.compare_pipelines import run_benchmark_suite
    return await run_in_threadpool(run_benchmark_suite)


@router.get("/llm-profiles")
def get_available_llm_profiles():
    """List LLM profiles the benchmark tools can switch between."""
    from app.rag.retrieval.llm_provider import AVAILABLE_LLM_PROFILES, get_active_llm
    active_prov, active_mod = get_active_llm()
    return {
        "active_provider": active_prov,
        "active_model": active_mod,
        "profiles": AVAILABLE_LLM_PROFILES,
    }


@router.post("/set-active-llm")
def set_active_llm_endpoint(provider: str, model: str | None = None):
    """Switch the benchmark LLM selection at runtime."""
    from app.rag.retrieval.llm_provider import get_active_llm, set_active_llm
    set_active_llm(provider=provider, model=model)
    active_prov, active_mod = get_active_llm()
    return {
        "message": f"Successfully switched active LLM to {active_prov} ({active_mod})",
        "active_provider": active_prov,
        "active_model": active_mod,
    }