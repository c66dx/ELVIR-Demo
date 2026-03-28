"""Evaluación por competencias en sesiones."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session as OrmSession

from app.models.assignment import Assignment
from app.models.competency import Competency
from app.models.competency_level import CompetencyLevel
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_competency import SessionCompetency
from app.schemas.session import SessionCompetenciesRequest


def replace_session_competencies(
    db: OrmSession,
    session_id: int,
    professional: Professional,
    data: SessionCompetenciesRequest,
) -> dict:
    """Reemplaza evaluación por competencias. Requiere asignación activa profesional–joven."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    assign = db.query(Assignment).filter(
        Assignment.youth_id == session.youth_id,
        Assignment.professional_id == professional.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    db.query(SessionCompetency).filter(SessionCompetency.session_id == session_id).delete()
    for item in data.items:
        comp = db.query(Competency).filter(Competency.slug == item.competency_slug, Competency.is_active == True).first()
        level = db.query(CompetencyLevel).filter(CompetencyLevel.slug == item.level_slug).first()
        if not comp or not level:
            raise HTTPException(
                status_code=400,
                detail=f"Competencia '{item.competency_slug}' o nivel '{item.level_slug}' no encontrado",
            )
        db.add(
            SessionCompetency(
                session_id=session_id,
                competency_id=comp.id,
                level_id=level.id,
                comment=item.comment,
            )
        )
    db.commit()
    return {"session_id": session_id, "items_count": len(data.items)}


def build_session_competencies_payload(db: OrmSession, session_id: int) -> dict:
    """Lista items de competencias para una sesión."""
    rows = (
        db.query(
            SessionCompetency.comment,
            Competency.slug,
            Competency.name,
            CompetencyLevel.slug,
            CompetencyLevel.label,
        )
        .join(Competency, Competency.id == SessionCompetency.competency_id)
        .join(CompetencyLevel, CompetencyLevel.id == SessionCompetency.level_id)
        .filter(SessionCompetency.session_id == session_id)
        .all()
    )
    items = [
        {
            "competency": {"slug": comp_slug, "name": comp_name},
            "level": {"slug": level_slug, "label": level_label},
            "comment": comment,
        }
        for comment, comp_slug, comp_name, level_slug, level_label in rows
    ]
    return {"session_id": session_id, "items": items}
