from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=True)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    citations = Column(JSON, nullable=True)
    execution_time = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="search_queries")
    parent_query = relationship("SearchQuery", remote_side=[id], backref="child_queries")
    feedbacks = relationship("Feedback", back_populates="query")