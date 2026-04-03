"""Modelo AUDIT_LOGS."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_role = Column(String(20), nullable=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(64), nullable=True, index=True)
    status_code = Column(Integer, nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
