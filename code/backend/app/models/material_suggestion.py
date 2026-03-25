"""Modelo MATERIAL_SUGGESTIONS."""
from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey, func

from app.database import Base


class MaterialSuggestion(Base):
    __tablename__ = "material_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    youth_id = Column(Integer, ForeignKey("youths.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("support_material.id"), nullable=False, index=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    suggested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
