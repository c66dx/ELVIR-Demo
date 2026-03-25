"""Modelo SIMULATION_TEMPLATES."""
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, UniqueConstraint, func

from app.database import Base


class SimulationTemplate(Base):
    __tablename__ = "simulation_templates"
    __table_args__ = (UniqueConstraint("job_role_id", "case_id", name="uq_job_role_case"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_role_id = Column(Integer, ForeignKey("job_roles.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    liveavatar_context_id = Column(String(255), nullable=False)
    liveavatar_avatar_id = Column(String(255), nullable=False)
    liveavatar_voice_id = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
