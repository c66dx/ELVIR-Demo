"""Comprobación de acceso a recursos de profesionales."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.professional import Professional
from app.models.user import User


def assert_can_access_professional(user: User, professional_id: int, db: Session) -> None:
    """Admin o el propio profesional; si no, 403."""
    if not can_access_professional(user, professional_id, db):
        raise HTTPException(status_code=403, detail="Acceso denegado")


def can_access_professional(user: User, professional_id: int, db: Session) -> bool:
    """Admin o el propio profesional."""
    if user.role == "ADMIN":
        return True
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        return prof is not None and prof.id == professional_id
    return False
