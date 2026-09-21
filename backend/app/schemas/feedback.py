from datetime import datetime
from pydantic import BaseModel, ConfigDict

class FeedbackCreate(BaseModel):
    query_id: int | None = None
    rating: int | None = None
    feedback_type: str | None = None
    comment: str | None = None

class FeedbackResponse(FeedbackCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    created_at: datetime