"""Modelo ASSIGNMENTS."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    youth_id = Column(Integer, ForeignKey("youths.id"), nullable=False, index=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # ACTIVO, INACTIVO
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
