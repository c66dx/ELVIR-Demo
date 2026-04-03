"""Modelo JOB_ROLES."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.database import Base


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    objetivo = Column(Text, nullable=True)
    competencias = Column(Text, nullable=True)  # arreglo JSON como texto
    is_active = Column(Boolean, nullable=False, default=True)
