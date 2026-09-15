from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SystemStatsResponse(BaseModel):
    total_documents: int
    total_projects: int
    total_queries: int
    total_users: int

class SystemVisitCreate(BaseModel):
    ip_address: str | None = None
    user_agent: str | None = None

class SystemVisitResponse(SystemVisitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visited_at: datetime