"""Modelo INTERVIEW_SUMMARIES."""
from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey, func
from sqlalchemy import JSON
from sqlalchemy.orm import relationship

from app.database import Base


class InterviewSummary(Base):
    __tablename__ = "interview_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True, index=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
    competency_tags = Column(JSON, nullable=True)  # ["comunicacion", "seguridad"]
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
