"""Modelo COMPETENCIES."""
from sqlalchemy import Column, Integer, String, Boolean, Text

from app.database import Base


class Competency(Base):
    __tablename__ = "competencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
