from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    workspace_id: str | None = Field(default=None, description="ID ของ Workspace/Session")
    query_text: str = Field(..., description="คำถามภาษาธรรมชาติจากผู้ใช้")
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior turns from the client. Capped at the latest 3 turns.",
    )
    parent_query_id: int | None = Field(
        default=None,
        description="Kept for database compatibility. The frontend does not send this.",
    )
    llm_provider: str | None = Field(
        default=None,
        description="Provider for this question only. The three chat winners use ollama.",
    )
    llm_model: str | None = Field(
        default=None,
        description="One of llama3.2:3b, qwen2.5:3b, or gemma3:4b for this question only.",
    )
    profile_name: str | None = Field(
        default=None,
        description="Winning preset paired with llm_model. Does not change the server default.",
    )

    @field_validator("llm_provider", "llm_model", "profile_name", mode="before")
    @classmethod
    def blank_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @field_validator("messages")
    @classmethod
    def cap_recent_turns(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        return value[-6:]

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
    document_id: int | None = None
    # Extra fields from retrieval payload (ignored by UI if unused)
    pages: list | None = None
    pages_formatted: str | None = None
    author: str | None = None
    advisor: str | None = None
    committee: str | None = None
    year: str | int | None = None
    school: str | None = None
    program: str | None = None

    model_config = ConfigDict(extra="ignore")

class ChatResponse(BaseModel):
    query_id: int | None = None
    workspace_id: str | None = None
    answer: str
    sources: list[str] = []
    citations: list[DocumentCitation] = []
    contexts_count: int = 0
    timing: TimingMetrics | None = None
    model: str | None = None
    preset: str | None = None
    performance: dict | None = None

class WorkspaceSummaryResponse(BaseModel):
    workspace_id: str
    title: str
    last_activity: datetime

class WorkspaceQueryResult(BaseModel):
    query_id: int
    query_text: str
    response_text: str | None = None
    retrieved_docs: dict | list | None = None

class WorkspaceDetailResponse(BaseModel):
    workspace_id: str
    queries: list[WorkspaceQueryResult]

class SearchQueryHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: str | None = None
    user_id: int | None = None
    parent_query_id: int | None = None
    query_text: str
    answer_text: str | None = None
    citations: dict | list | None = None
    execution_time: dict | None = None
    created_at: datetime