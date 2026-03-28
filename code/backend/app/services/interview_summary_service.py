"""Creación y lectura de resúmenes cualitativos de entrevistas."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.interview_summary import InterviewSummary
from app.models.session import Session as SessionModel
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.services.notifications import upsert_youth_notification


def summary_response_dict(summary: InterviewSummary) -> dict:
    return {
        "id": summary.id,
        "session_id": summary.session_id,
        "professional_id": summary.professional_id,
        "summary_text": summary.summary_text,
        "competency_tags": summary.competency_tags,
        "created_at": summary.created_at.isoformat(),
        "updated_at": summary.updated_at.isoformat(),
    }


def create_or_update_professional_summary(
    db: Session,
    session_id: int,
    prof: Professional,
    summary_text: str,
    competency_tags: Optional[list[str]],
) -> dict:
    """Crea o actualiza resumen; notifica al joven. Requiere que el caller haya validado asignación."""
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
        existing.summary_text = summary_text
        existing.competency_tags = competency_tags
        existing.professional_id = prof.id
        upsert_youth_notification(
            db,
            youth_id=session.youth_id,
            type="feedback",
            title="Retroalimentacion disponible",
            message="Hay comentarios del tutor sobre tu entrevista.",
            link=f"/joven/retroalimentacion/{session_id}",
            entity_type="interview_summary",
            entity_id=existing.id,
        )
        db.commit()
        db.refresh(existing)
        return summary_response_dict(existing)

    summary = InterviewSummary(
        session_id=session_id,
        professional_id=prof.id,
        summary_text=summary_text,
        competency_tags=competency_tags,
    )
    db.add(summary)
    db.flush()
    upsert_youth_notification(
        db,
        youth_id=session.youth_id,
        type="feedback",
        title="Retroalimentacion disponible",
        message="Hay comentarios del tutor sobre tu entrevista.",
        link=f"/joven/retroalimentacion/{session_id}",
        entity_type="interview_summary",
        entity_id=summary.id,
    )
    db.commit()
    db.refresh(summary)
    return summary_response_dict(summary)


def get_summary_for_session_if_access(
    db: Session,
    session_id: int,
) -> InterviewSummary | None:
    """Devuelve InterviewSummary o None. El caller debe haber validado acceso a la sesión."""
    return db.query(InterviewSummary).filter(InterviewSummary.session_id == session_id).first()
