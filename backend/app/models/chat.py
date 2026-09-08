# app/models/search_query.py
from sqlalchemy import Column, Integer, Text, ForeignKey, JSON, DateTime
from app.core.database import Base

class SearchQuery(Base):
    __tablename__ = "search_queries"

    query_id = Column(Integer, primary_key=True, index=True)
    
    # เอา ForeignKey("users.user_id") ออก เหลือแค่ Integer ธรรมดา
    user_id = Column(Integer, nullable=True) 
    
    parent_query_id = Column(Integer, ForeignKey("search_queries.query_id"), nullable=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    retrieved_docs = Column(JSON, nullable=True)