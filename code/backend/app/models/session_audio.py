"""Modelo SESSION_AUDIO."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class SessionAudio(Base):
    __tablename__ = "session_audios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True, index=True)
    url = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
