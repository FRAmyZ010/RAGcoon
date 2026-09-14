import json
import uuid
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.search_query import SearchQuery
from app.schemas.chat import (
    ChatResponse,
    TimingMetrics,
    DocumentCitation,
    SearchQueryHistoryResponse,
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspaceQueryResult,
)
from app.rag.retrieval import stream_answer_question

def process_rag_query(
    db: Session,
    query_text: str,
    workspace_id: str | None = None,
    parent_query_id: int | None = None
) -> ChatResponse:
    """
    ประมวลผลคำถาม RAG แบบ Blocking (Non-Streaming) และบันทึกประวัติลง PostgreSQL
    """
    active_workspace_id = workspace_id or f"ws-{uuid.uuid4().hex[:12]}"
    try:
        from app.rag.main import answer_question
        rag_output = answer_question(query_text)
        answer_text = rag_output.get("answer", "")
        citations_data = rag_output.get("citations", [])
        timing_data = rag_output.get("timing", {})
    except ImportError:
        answer_text = f"ระบบได้รับคำถาม: '{query_text}' เรียบร้อยแล้ว"
        citations_data = [{
            "project_title": "RAGcoon System",
            "source": "Senior_Project_Archive.pdf",
            "page": 1,
            "content_snippet": "เนื้อหาตัวอย่างจากเอกสารอ้างอิง"
        }]
        timing_data = {"retrieval_seconds": 0.1, "llm_seconds": 1.2, "total_seconds": 1.3}

    citations = [DocumentCitation(**c) if isinstance(c, dict) else c for c in citations_data]
    timing = TimingMetrics(**timing_data) if isinstance(timing_data, dict) else timing_data

    db_entry = SearchQuery(
        workspace_id=active_workspace_id,
        query_text=query_text,
        parent_query_id=parent_query_id,
        answer_text=answer_text,
        citations=[c.model_dump() for c in citations],
        execution_time=timing.model_dump() if timing else None
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return ChatResponse(
        query_id=db_entry.id,
        workspace_id=active_workspace_id,
        answer=answer_text,
        sources=[c.source for c in citations],
        citations=citations,
        contexts_count=len(citations),
        timing=timing
    )

def process_rag_stream(
    db: Session,
    query_text: str,
    workspace_id: str | None = None,
    parent_query_id: int | None = None
) -> Generator[str, None, None]:
    """
    สร้าง Record ใน DB, สตรีมมิ่ง SSE Events ไปยัง Frontend และบันทึกคำตอบฉบับเต็มเมื่อสตรีมจบ
    """
    active_workspace_id = workspace_id or f"ws-{uuid.uuid4().hex[:12]}"

    db_entry = SearchQuery(
        workspace_id=active_workspace_id,
        query_text=query_text,
        parent_query_id=parent_query_id,
        answer_text="",
        citations=[]
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    full_answer = ""
    citations_data = []
    execution_time_data = {}

    for item in stream_answer_question(question=query_text):
        event_type = item.get("event", "message")
        event_data = item.get("data", {})

        if event_type == "metadata":
            citations_data = event_data.get("citations", [])
        elif event_type == "token":
            token_text = event_data.get("token", "")
            full_answer += token_text
            chunk_payload = {
                "type": "answer_chunk",
                "content": token_text,
                "workspace_id": active_workspace_id
            }
            yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
        elif event_type == "done":
            full_answer = event_data.get("answer", full_answer)
            citations_data = event_data.get("citations", citations_data)
            execution_time_data = event_data.get("timing", {})

    metadata_payload = {
        "type": "metadata",
        "workspace_id": active_workspace_id,
        "citations": citations_data,
        "timing": execution_time_data
    }
    yield f"data: {json.dumps(metadata_payload, ensure_ascii=False)}\n\n"

    db_entry.answer_text = full_answer
    db_entry.citations = citations_data
    db_entry.execution_time = execution_time_data
    db.commit()

def get_chat_history(db: Session, skip: int = 0, limit: int = 20) -> list[SearchQueryHistoryResponse]:
    queries = db.query(SearchQuery).order_by(SearchQuery.created_at.desc()).offset(skip).limit(limit).all()
    return queries

def get_all_workspaces(db: Session) -> list[WorkspaceSummaryResponse]:
    """
    ดึงรายการ Workspace ทั้งหมดเรียงตามกิจกรรมล่าสุด
    """
    results = (
        db.query(
            SearchQuery.workspace_id,
            func.min(SearchQuery.query_text).label("title"),
            func.max(SearchQuery.created_at).label("last_activity")
        )
        .filter(SearchQuery.workspace_id.isnot(None))
        .group_by(SearchQuery.workspace_id)
        .order_by(func.max(SearchQuery.created_at).desc())
        .all()
    )

    workspaces = []
    for r in results:
        title = r.title[:30] + "..." if len(r.title) > 30 else r.title
        workspaces.append(
            WorkspaceSummaryResponse(
                workspace_id=r.workspace_id,
                title=title or "บทสนทนาใหม่",
                last_activity=r.last_activity
            )
        )
    return workspaces

def get_workspace_detail(db: Session, workspace_id: str) -> WorkspaceDetailResponse | None:
    """
    ดึงประวัติคำถาม-คำตอบทั้งหมดใน Workspace ที่ระบุ
    """
    queries = (
        db.query(SearchQuery)
        .filter(SearchQuery.workspace_id == workspace_id)
        .order_by(SearchQuery.created_at.asc())
        .all()
    )

    if not queries:
        return None

    query_list = []
    for q in queries:
        query_list.append(
            WorkspaceQueryResult(
                query_id=q.id,
                query_text=q.query_text,
                response_text=q.answer_text or "",
                retrieved_docs={"citations": q.citations or [], "timing": q.execution_time or {}}
            )
        )

    return WorkspaceDetailResponse(
        workspace_id=workspace_id,
        queries=query_list
    )