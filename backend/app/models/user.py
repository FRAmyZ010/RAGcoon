from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    role = relationship("Role", back_populates="users")
    created_projects = relationship("Project", back_populates="creator")
    uploaded_documents = relationship("Document", back_populates="uploader")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user")
    feedbacks = relationship("FeedbackIssue", foreign_keys="[FeedbackIssue.user_id]", back_populates="user")
    reviewed_feedbacks = relationship("FeedbackIssue", foreign_keys="[FeedbackIssue.reviewed_by]", back_populates="reviewer")
    rag_configs = relationship("RAGConfiguration", back_populates="configured_by_user")
    system_logs = relationship("SystemLog", back_populates="user")