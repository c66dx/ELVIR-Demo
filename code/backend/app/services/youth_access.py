"""Carga de jóvenes y comprobación de acceso (lectura) para routers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth


def load_youth_or_404(db: Session, youth_id: int) -> Youth:
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    return youth


def require_youth_assigned_to_professional(
    db: Session,
    youth_id: int,
    prof: Professional,
) -> Youth:
    """Carga el joven y exige asignación ACTIVO entre el joven y el profesional autenticado."""
    youth = load_youth_or_404(db, youth_id)
    assign = (
        db.query(Assignment)
        .filter(
            Assignment.youth_id == youth_id,
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        )
        .first()
    )
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return youth


def ensure_youth_read_access(db: Session, user: User, youth: Youth) -> None:
    """Permite ADMIN; JOVEN solo su ficha; PROFESIONAL solo con asignación ACTIVA (si tiene fila Professional)."""
    if user.role == "ADMIN":
        return
    if user.role == "JOVEN":
        if youth.user_id != user.id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            assign = (
                db.query(Assignment)
                .filter(
                    Assignment.youth_id == youth.id,
                    Assignment.professional_id == prof.id,
                    Assignment.status == "ACTIVO",
                )
                .first()
            )
            if not assign:
                raise HTTPException(status_code=403, detail="Acceso denegado")
        return
    raise HTTPException(status_code=403, detail="Acceso denegado")


def ensure_youth_photo_upload_access(db: Session, user: User, youth: Youth) -> None:
    """Subida de foto: ADMIN; JOVEN propio; PROFESIONAL con fila y asignación ACTIVA."""
    if user.role == "ADMIN":
        return
    if user.role == "JOVEN":
        if youth.user_id != user.id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        assign = (
            db.query(Assignment)
            .filter(
                Assignment.youth_id == youth.id,
                Assignment.professional_id == prof.id,
                Assignment.status == "ACTIVO",
            )
            .first()
        )
        if not assign:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return
    raise HTTPException(status_code=403, detail="Acceso denegado")
