"""Modelo MATERIAL_VIEWS."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func

from app.database import Base


class MaterialView(Base):
    __tablename__ = "material_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    youth_id = Column(Integer, ForeignKey("youths.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("support_material.id"), nullable=False, index=True)
    seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
