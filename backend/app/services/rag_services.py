import json
import logging
import uuid
from typing import Generator
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.search_query import SearchQuery
from app.schemas.chat import (
    ChatMessage,
    ChatResponse,
    TimingMetrics,
    DocumentCitation,
    SearchQueryHistoryResponse,
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspaceQueryResult,
)
from app.rag.retrieval import answer_question, stream_answer_question
from app.rag.retrieval.prescreen import prescreen_reply
from app.rag.retrieval.session_manager import session_manager
from app.services.document_service import enrich_citations_with_document_ids

logger = logging.getLogger(__name__)
MAX_CONTEXT_TURNS = 3


def sync_client_messages(workspace_id: str | None, messages: list[ChatMessage] | None) -> None:
    """Replace in-memory session history with the latest client turns."""
    if not workspace_id:
        return
    session_manager.clear_session(workspace_id)
    recent = list(messages or [])[-(MAX_CONTEXT_TURNS * 2):]
    for message in recent:
        if message.role not in ("user", "assistant") or not message.content.strip():
            continue
        session_manager.add_message(workspace_id, message.role, message.content)


def _open_db():
    from app.core.database import SessionLocal

    return SessionLocal()


def _enrich_citations(citations: list | None) -> list:
    db = _open_db()
    try:
        return enrich_citations_with_document_ids(db, citations or [])
    except Exception:
        logger.exception("Failed to enrich citations")
        return list(citations or [])
    finally:
        db.close()


def create_search_query_row(
    *,
    workspace_id: str,
    query_text: str,
    parent_query_id: int | None,
) -> int | None:
    db = _open_db()
    try:
        entry = SearchQuery(
            workspace_id=workspace_id,
            query_text=query_text,
            parent_query_id=parent_query_id,
            answer_text="",
            citations=[],
            execution_time={},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    except Exception:
        logger.exception("Failed to create search_queries row")
        db.rollback()
        return None
    finally:
        db.close()


def persist_search_query_log(
    *,
    query_id: int | None,
    workspace_id: str,
    query_text: str,
    parent_query_id: int | None,
    answer_text: str,
    citations: list,
    sources: list,
    execution_time: dict | None,
) -> None:
    """Background log for completed and interrupted streams."""
    timing = dict(execution_time or {})
    timing["sources"] = sources
    db = _open_db()
    try:
        entry = db.get(SearchQuery, query_id) if query_id else None
        if entry is None:
            entry = SearchQuery(
                workspace_id=workspace_id,
                query_text=query_text,
                parent_query_id=parent_query_id,
            )
            db.add(entry)
        entry.answer_text = answer_text
        entry.citations = citations
        entry.execution_time = timing
        db.commit()
    except Exception:
        logger.exception("Failed to log search_queries row")
        db.rollback()
    finally:
        db.close()

def process_rag_query(
    db: Session,
    query_text: str,
    workspace_id: str | None = None,
    parent_query_id: int | None = None,
    messages: list[ChatMessage] | None = None,
) -> ChatResponse:
    """
    ประมวลผลคำถาม RAG แบบ Blocking (Non-Streaming) และบันทึกประวัติลง PostgreSQL
    """
    active_workspace_id = workspace_id or f"ws-{uuid.uuid4().hex[:12]}"
    sync_client_messages(active_workspace_id, messages)
    canned = prescreen_reply(query_text)
    try:
        rag_output = (
            {"answer": canned, "citations": [], "timing": {}}
            if canned
            else answer_question(query_text, session_id=active_workspace_id)
        )
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

    citations_data = enrich_citations_with_document_ids(db, citations_data)
    citations = [DocumentCitation(**c) if isinstance(c, dict) else c for c in citations_data]
    if isinstance(timing_data, dict):
        timing = TimingMetrics(
            retrieval_seconds=float(timing_data.get("retrieval_seconds", 0.0) or 0.0),
            rerank_seconds=float(timing_data.get("rerank_seconds", 0.0) or 0.0),
            llm_seconds=float(timing_data.get("llm_seconds", 0.0) or 0.0),
            total_seconds=float(timing_data.get("total_seconds", 0.0) or 0.0),
        )
    else:
        timing = timing_data

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
    parent_query_id: int | None = None,
    messages: list[ChatMessage] | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> Generator[str, None, None]:
    """
    Sync client history, stream SSE, and log the turn via BackgroundTasks
    even when the stream fails midway.
    """
    active_workspace_id = workspace_id or f"ws-{uuid.uuid4().hex[:12]}"
    sync_client_messages(active_workspace_id, messages)

    query_id = create_search_query_row(
        workspace_id=active_workspace_id,
        query_text=query_text,
        parent_query_id=parent_query_id,
    )

    full_answer = ""
    citations_data: list = []
    sources: list = []
    execution_time_data: dict = {}
    model_name = None

    try:
        canned = prescreen_reply(query_text)
        events = (
            (
                {"event": "token", "data": {"token": canned}},
                {"event": "done", "data": {"answer": canned, "citations": [], "sources": [], "timing": {}}},
            )
            if canned
            else stream_answer_question(question=query_text, session_id=active_workspace_id)
        )
        for item in events:
            event_type = item.get("event", "message")
            event_data = item.get("data", {})

            if event_type == "metadata":
                citations_data = _enrich_citations(event_data.get("citations", []))
                sources = list(event_data.get("sources") or [])
                if event_data.get("model"):
                    model_name = event_data.get("model")
                if event_data.get("timing"):
                    execution_time_data = event_data.get("timing") or {}
            elif event_type == "token":
                token_text = event_data.get("token", "")
                full_answer += token_text
                chunk_payload = {
                    "type": "answer_chunk",
                    "content": token_text,
                    "workspace_id": active_workspace_id,
                    "query_id": query_id,
                }
                yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
            elif event_type == "error":
                error_text = event_data.get("error") or "Stream error"
                if not full_answer:
                    full_answer = error_text
                execution_time_data = {
                    **execution_time_data,
                    "error": error_text,
                }
            elif event_type == "done":
                full_answer = event_data.get("answer", full_answer)
                citations_data = _enrich_citations(
                    event_data.get("citations", citations_data)
                )
                sources = list(event_data.get("sources") or sources)
                execution_time_data = event_data.get("timing", execution_time_data)
                if event_data.get("model"):
                    model_name = event_data.get("model")

        metadata_payload = {
            "type": "metadata",
            "workspace_id": active_workspace_id,
            "query_id": query_id,
            "citations": citations_data,
            "timing": execution_time_data,
            "model": model_name,
        }
        yield f"data: {json.dumps(metadata_payload, ensure_ascii=False)}\n\n"
    except Exception as exc:
        logger.exception("RAG stream failed")
        if not full_answer:
            full_answer = f"Stream error: {exc}"
        execution_time_data = {**execution_time_data, "error": str(exc)}
        raise
    finally:
        log_task = persist_search_query_log
        log_kwargs = {
            "query_id": query_id,
            "workspace_id": active_workspace_id,
            "query_text": query_text,
            "parent_query_id": parent_query_id,
            "answer_text": full_answer,
            "citations": citations_data,
            "sources": sources,
            "execution_time": execution_time_data,
        }
        if background_tasks is not None:
            background_tasks.add_task(log_task, **log_kwargs)
        else:
            log_task(**log_kwargs)

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