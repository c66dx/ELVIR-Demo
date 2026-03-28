"""Persistencia de evaluación externa (ej. webhook LiveAvatar)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as OrmSession

from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.schemas.session import SessionEvaluationRequest


def persist_liveavatar_evaluation(
    db: OrmSession,
    data: SessionEvaluationRequest,
    request_id: str,
) -> int:
    """Guarda evaluación en session.metrics y evento LIVEAVATAR_EVALUATION. Devuelve session.id."""
    if not data.session_id and not data.liveavatar_session_id:
        raise HTTPException(status_code=400, detail="session_id o liveavatar_session_id requerido")

    session = None
    if data.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == data.session_id).first()
    elif data.liveavatar_session_id:
        session = db.query(SessionModel).filter(
            SessionModel.liveavatar_session_id == data.liveavatar_session_id
        ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    metrics = dict(session.metrics) if session.metrics else {}
    metrics["liveavatar_evaluation"] = data.evaluation
    metrics["liveavatar_evaluation_source"] = data.source or "liveavatar"
    metrics["liveavatar_evaluation_received_at"] = datetime.now(timezone.utc).isoformat()
    session.metrics = metrics

    db.add(
        SessionEvent(
            session_id=session.id,
            event_type="LIVEAVATAR_EVALUATION",
            payload={"source": data.source or "liveavatar", "request_id": request_id},
        )
    )
    db.commit()
    return session.id
