"""Router de resúmenes cualitativos."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interview_summary import InterviewSummary
from app.models.session import Session as SessionModel
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.core.dependencies import get_current_user, get_current_professional

router = APIRouter(tags=["summaries"])


def _check_session_access(db: Session, user: User, session_id: int) -> bool:
    """Verifica si el usuario puede acceder a la sesión (joven propio o profesional asignado)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return False
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        return youth and youth.id == session.youth_id
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return False
        assign = db.query(Assignment).filter(
            Assignment.youth_id == session.youth_id,
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        ).first()
        return assign is not None
    return False


class SummaryRequest(BaseModel):
    summary_text: str
    competency_tags: Optional[list[str]] = None


@router.post("/sessions/{session_id}/summary")
def create_or_update_summary(
    session_id: int,
    data: SummaryRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Crea o actualiza resumen cualitativo de una sesión. Solo profesional asignado."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == session.youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    existing = db.query(InterviewSummary).filter(InterviewSummary.session_id == session_id).first()
    if existing:
        existing.summary_text = data.summary_text
        existing.competency_tags = data.competency_tags
        existing.professional_id = prof.id
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "session_id": existing.session_id,
            "professional_id": existing.professional_id,
            "summary_text": existing.summary_text,
            "competency_tags": existing.competency_tags,
            "created_at": existing.created_at.isoformat(),
            "updated_at": existing.updated_at.isoformat(),
        }
    summary = InterviewSummary(
        session_id=session_id,
        professional_id=prof.id,
        summary_text=data.summary_text,
        competency_tags=data.competency_tags,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return {
        "id": summary.id,
        "session_id": summary.session_id,
        "professional_id": summary.professional_id,
        "summary_text": summary.summary_text,
        "competency_tags": summary.competency_tags,
        "created_at": summary.created_at.isoformat(),
        "updated_at": summary.updated_at.isoformat(),
    }


@router.get("/sessions/{session_id}/summary")
def get_session_summary(
    session_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene resumen cualitativo de una sesión. Requiere acceso a la sesión."""
    if not _check_session_access(db, user, session_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    summary = db.query(InterviewSummary).filter(InterviewSummary.session_id == session_id).first()
    if not summary:
        return None
    return {
        "id": summary.id,
        "session_id": summary.session_id,
        "professional_id": summary.professional_id,
        "summary_text": summary.summary_text,
        "competency_tags": summary.competency_tags,
        "created_at": summary.created_at.isoformat(),
        "updated_at": summary.updated_at.isoformat(),
    }

