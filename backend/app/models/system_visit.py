from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class SystemVisit(Base):
    __tablename__ = "system_visits"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    visited_at = Column(DateTime(timezone=True), server_default=func.now())