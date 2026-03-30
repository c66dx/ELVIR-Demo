"""Modelo PROFESSIONAL_INVITATIONS."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class ProfessionalInvitation(Base):
    __tablename__ = "professional_invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
