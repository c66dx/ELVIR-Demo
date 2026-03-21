"""Modelo YOUTH_NOTIFICATIONS."""
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, func, UniqueConstraint

from app.database import Base


class YouthNotification(Base):
    __tablename__ = "youth_notifications"
    __table_args__ = (
        UniqueConstraint("youth_id", "entity_type", "entity_id", name="uq_youth_notifications_entity"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    youth_id = Column(Integer, ForeignKey("youths.id"), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)
    entity_type = Column(String(32), nullable=True)
    entity_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
