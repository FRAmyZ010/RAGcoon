from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SystemStatsResponse(BaseModel):
    total_documents: int
    total_projects: int
    total_queries: int
    total_users: int

class YearCount(BaseModel):
    year: int | None = None
    count: int

class DayCount(BaseModel):
    day: str
    count: int

class KeywordCount(BaseModel):
    keyword: str
    count: int

class OverviewResponse(BaseModel):
    total_documents: int
    total_projects: int
    total_queries: int
    total_feedbacks: int
    total_visits: int
    documents_by_year: list[YearCount]
    searches_by_day: list[DayCount]
    top_keywords: list[KeywordCount]

class SystemVisitCreate(BaseModel):
    ip_address: str | None = None
    user_agent: str | None = None

class SystemVisitResponse(SystemVisitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visited_at: datetime