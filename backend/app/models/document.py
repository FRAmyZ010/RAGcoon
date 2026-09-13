from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    title = Column(String(255), nullable=True)
    supervisory_committee = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")
    upload_date = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="documents")