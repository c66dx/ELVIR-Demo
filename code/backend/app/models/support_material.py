"""Modelo SUPPORT_MATERIAL."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class SupportMaterial(Base):
    __tablename__ = "support_material"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), nullable=False)  # VIDEO, PDF, LINK
    url = Column(String(500), nullable=False)
    job_role_id = Column(Integer, ForeignKey("job_roles.id"), nullable=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)
    created_by = Column(
        Integer, ForeignKey("professionals.id"), nullable=True, index=True
    )  # nulo = Admin; valor = Profesional
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
