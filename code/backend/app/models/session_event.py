"""Modelo SESSION_EVENTS."""
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from app.database import Base


class SessionEvent(Base):
    __tablename__ = "session_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload = Column(JSON, nullable=True)
