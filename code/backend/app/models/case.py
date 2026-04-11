"""Modelo CASES."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    difficulty = Column(String(20), nullable=False)  # NORMAL, BAJA, MEDIA, ALTA
    prompt_instructions = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    intervencion_regulacion_emocional = Column(Text, nullable=True)
    intervencion_presentacion_personal = Column(Text, nullable=True)
    intervencion_expectativas_empresa = Column(Text, nullable=True)
    opening_text = Column(String(500), nullable=True)  # Saludo inicial por caso (opcional)
    is_active = Column(Boolean, nullable=False, default=True)
