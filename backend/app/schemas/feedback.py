from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeedbackType = Literal["Suggestion", "Bug", "Others"]
FeedbackStatus = Literal["Open", "In Progress", "Resolved"]


class FeedbackCreate(BaseModel):
    submitter_name: str = Field(min_length=1, max_length=120)
    contact_gmail: bool = False
    contact_phone: bool = False
    rating: int = Field(ge=1, le=5)
    feedback_type: FeedbackType
    comment: str = Field(min_length=1)
    query_id: int | None = None


class FeedbackStatusUpdate(BaseModel):
    status: FeedbackStatus


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submitter_name: str | None = None
    contact_gmail: bool = False
    contact_phone: bool = False
    rating: int | None = None
    feedback_type: str | None = None
    comment: str | None = None
    attachment_name: str | None = None
    status: str = "Open"
    query_id: int | None = None
    user_id: int | None = None
    created_at: datetime
