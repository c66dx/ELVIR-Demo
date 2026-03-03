"""Modelo COMPETENCY_LEVELS."""
from sqlalchemy import Column, Integer, String

from app.database import Base


class CompetencyLevel(Base):
    __tablename__ = "competency_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    label = Column(String(100), nullable=False)
    sort_order = Column(Integer, nullable=False, default=1)
