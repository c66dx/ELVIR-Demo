"""Modelo SESSION_COMPETENCIES."""
from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey, UniqueConstraint, func
from app.database import Base


class SessionCompetency(Base):
    __tablename__ = "session_competencies"
    __table_args__ = (UniqueConstraint("session_id", "competency_id", name="uq_session_competency"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    competency_id = Column(Integer, ForeignKey("competencies.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("competency_levels.id"), nullable=False, index=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
