from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ChatRequest(BaseModel):
    query_text: str = Field(..., description="คำถามภาษาธรรมชาติจากผู้ใช้")
    parent_query_id: int | None = Field(default=None, description="ID ของคำถามก่อนหน้าเพื่อดึงบริบทแชท")
    workspace_id: int | None = Field(default=None, description="ID ของ Workspace/Session")

class TimingMetrics(BaseModel):
    retrieval_seconds: float = 0.0
    rerank_seconds: float = 0.0
    llm_seconds: float = 0.0
    total_seconds: float = 0.0

class DocumentCitation(BaseModel):
    project_title: str | None = None
    source: str
    page: int | None = None
    content_snippet: str | None = None

class ChatResponse(BaseModel):
    query_id: int | None = None
    answer: str
    sources: list[str] = []
    citations: list[DocumentCitation] = []
    contexts_count: int = 0
    timing: TimingMetrics | None = None

class SearchQueryHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    parent_query_id: int | None = None
    query_text: str
    answer_text: str | None = None
    citations: dict | list | None = None
    execution_time: dict | None = None
    created_at: datetime