from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ChatRequest(BaseModel):
    query_text: str
    user_id: Optional[int] = None
    parent_query_id: Optional[int] = None

class DocumentCitation(BaseModel):
    document_id: int
    title: str
    page: Optional[int] = None
    content: Optional[str] = None
    score: float

class ChatResponse(BaseModel):
    query_id: int
    response_text: str
    retrieved_docs: List[DocumentCitation] = []
    created_at: datetime
