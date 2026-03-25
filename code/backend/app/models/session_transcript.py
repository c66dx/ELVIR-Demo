"""Modelo SESSION_TRANSCRIPTS."""
from sqlalchemy import Column, DateTime, Integer, ForeignKey, Boolean, func
from sqlalchemy import JSON

from app.database import Base


class SessionTranscript(Base):
    __tablename__ = "session_transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True, index=True)
    transcript_data = Column(JSON, nullable=False)  # elementos con claves: role, transcript, absolute_timestamp, relative_timestamp
    session_active = Column(Boolean, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
