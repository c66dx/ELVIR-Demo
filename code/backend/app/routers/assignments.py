"""Router de asignaciones (joven–profesional)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.youth import Youth
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


class AssignmentCreate(BaseModel):
    youth_id: int
    professional_id: int


@router.post("")
def create_assignment(
    data: AssignmentCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Asigna un joven a un profesional. Admin o profesional (solo a sí mismo)."""
    youth = db.query(Youth).filter(Youth.id == data.youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    prof = db.query(Professional).filter(Professional.id == data.professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    if user.role == "ADMIN":
        pass
    elif user.role == "PROFESIONAL":
        my_prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not my_prof or my_prof.id != data.professional_id:
            raise HTTPException(status_code=403, detail="Solo puede asignar jóvenes a su propio perfil")
    else:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    existing = db.query(Assignment).filter(
        Assignment.youth_id == data.youth_id,
        Assignment.professional_id == data.professional_id,
        Assignment.status == "ACTIVO",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una asignación activa")
    assignment = Assignment(
        youth_id=data.youth_id,
        professional_id=data.professional_id,
        status="ACTIVO",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {
        "id": assignment.id,
        "youth_id": assignment.youth_id,
        "professional_id": assignment.professional_id,
        "status": assignment.status,
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        "ended_at": assignment.ended_at.isoformat() if assignment.ended_at else None,
    }


@router.patch("/{assignment_id}/end")
def end_assignment(
    assignment_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Finaliza una asignación (status INACTIVO). Profesional asignado o Admin."""
    from datetime import datetime, timezone

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    if user.role == "ADMIN":
        pass
    elif user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof or prof.id != assignment.professional_id:
            raise HTTPException(status_code=403, detail="Solo puede finalizar sus propias asignaciones")
    else:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    assignment.status = "INACTIVO"
    assignment.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return {
        "id": assignment.id,
        "status": assignment.status,
        "ended_at": assignment.ended_at.isoformat() if assignment.ended_at else None,
    }
