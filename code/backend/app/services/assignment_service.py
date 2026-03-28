"""Creación y cierre de asignaciones joven–profesional."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth


def get_assignment_or_404(db: Session, assignment_id: int) -> Assignment:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return assignment


def create_active_assignment(
    db: Session,
    youth_id: int,
    professional_id: int,
) -> Assignment:
    """Crea asignación ACTIVO si joven y profesional existen y no hay duplicado activo."""
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    prof = db.query(Professional).filter(Professional.id == professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    existing = db.query(Assignment).filter(
        Assignment.youth_id == youth_id,
        Assignment.professional_id == professional_id,
        Assignment.status == "ACTIVO",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una asignación activa")
    assignment = Assignment(
        youth_id=youth_id,
        professional_id=professional_id,
        status="ACTIVO",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def assignment_created_payload(assignment: Assignment) -> dict:
    return {
        "id": assignment.id,
        "youth_id": assignment.youth_id,
        "professional_id": assignment.professional_id,
        "status": assignment.status,
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        "ended_at": assignment.ended_at.isoformat() if assignment.ended_at else None,
    }


def finalize_assignment(db: Session, assignment: Assignment) -> Assignment:
    assignment.status = "INACTIVO"
    assignment.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment


def assignment_ended_payload(assignment: Assignment) -> dict:
    return {
        "id": assignment.id,
        "status": assignment.status,
        "ended_at": assignment.ended_at.isoformat() if assignment.ended_at else None,
    }


def assert_user_can_create_assignment(db: Session, user: User, professional_id: int) -> None:
    """Admin o profesional asignándose a sí mismo."""
    if user.role == "ADMIN":
        return
    if user.role == "PROFESIONAL":
        my_prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not my_prof or my_prof.id != professional_id:
            raise HTTPException(status_code=403, detail="Solo puede asignar jóvenes a su propio perfil")
        return
    raise HTTPException(status_code=403, detail="Acceso denegado")


def assert_user_can_end_assignment(db: Session, user: User, assignment: Assignment) -> None:
    """Admin o el profesional dueño de la asignación."""
    if user.role == "ADMIN":
        return
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof or prof.id != assignment.professional_id:
            raise HTTPException(status_code=403, detail="Solo puede finalizar sus propias asignaciones")
        return
    raise HTTPException(status_code=403, detail="Acceso denegado")
