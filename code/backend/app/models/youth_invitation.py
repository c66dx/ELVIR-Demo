"""Modelo YOUTH_INVITATIONS."""
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class YouthInvitation(Base):
    __tablename__ = "youth_invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    youth_id = Column(Integer, ForeignKey("youths.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
