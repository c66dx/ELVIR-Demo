"""Modelo YOUTH."""
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, ForeignKey, func

from app.database import Base


class Youth(Base):
    __tablename__ = "youths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    login_enabled = Column(Boolean, nullable=False, default=False)
    display_name = Column(String(255), nullable=False)
    identifier = Column(String(100), nullable=True, unique=True, index=True)
    rut = Column(String(20), nullable=True, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    year_of_birth = Column(Integer, nullable=True)
    diagnosis = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    general_notes = Column(Text, nullable=True)
    profile_checklist = Column(Text, nullable=True)  # arreglo JSON: ["comunicacion", "trabajo_equipo", ...]
    photo_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
