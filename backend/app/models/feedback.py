from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=True)
    submitter_name = Column(String(120), nullable=True)
    contact_gmail = Column(Boolean, nullable=False, default=False, server_default="false")
    contact_phone = Column(Boolean, nullable=False, default=False, server_default="false")
    rating = Column(Integer, nullable=True)
    feedback_type = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_path = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="Open", server_default="Open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="feedbacks")
    query = relationship("SearchQuery", back_populates="feedbacks")