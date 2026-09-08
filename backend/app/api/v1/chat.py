import logging
from typing import Any, cast
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.rag.retrieval import answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & RAG"])


# --- Pydantic Schemas ---

class ChatRequest(BaseModel):
    query_text: str = Field(
        ...,
        description="คำถามภาษาธรรมชาติจากผู้ใช้",
        example="ระบบ Petfeeder มีขั้นตอนการทำงานอย่างไร"
    )


class TimingMetrics(BaseModel):
    retrieval_seconds: float
    rerank_seconds: float
    llm_seconds: float
    total_seconds: float


class ChatResponse(BaseModel):
    answer: str
    model: str = Field(..., description="ชื่อโมเดล LLM ที่ใช้สร้างคำตอบ", example="llama3.2")
    sources: list[str]
    contexts_count: int
    timing: TimingMetrics


# --- API Endpoint ---

@router.post("/query", response_model=ChatResponse)
async def chat_with_rag(payload: ChatRequest):
    """
    Endpoint สำหรับรับคำถามจาก Frontend ส่งต่อไปประมวลผลผ่าน RAG Engine
    และ คืนค่าคำตอบ, ชื่อโมเดลที่ใช้ พร้อม Citations/Sources
    """
    try:
        raw_result = await run_in_threadpool(answer_question, payload.query_text)
        result = cast(dict[str, Any], raw_result)

        timing_data = cast(dict[str, float], result.get("timing", {}))
        metrics = TimingMetrics(
            retrieval_seconds=timing_data.get("retrieval_seconds", 0.0),
            rerank_seconds=timing_data.get("rerank_seconds", 0.0),
            llm_seconds=timing_data.get("llm_seconds", 0.0),
            total_seconds=timing_data.get("total_seconds", 0.0)
        )

        contexts = cast(list[str], result.get("contexts", []))
        sources = cast(list[str], result.get("sources", []))

        # ดึงชื่อโมเดลจาก result (ถ้าไม่มีให้ตั้งค่า default fallback ไว้)
        model_used = str(result.get("model", "llama3.2"))

        return ChatResponse(
            answer=result.get("answer", ""),
            model=model_used,
            sources=sources,
            contexts_count=len(contexts),
            timing=metrics
        )

    except Exception as e:
        logger.error(f"Error occurred while processing RAG query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the RAG query: {str(e)}"
        )