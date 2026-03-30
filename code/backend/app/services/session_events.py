"""Eventos de trazabilidad manuales en sesiones."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session as OrmSession

from app.models.session_event import SessionEvent
from app.schemas.session import SessionEventCreate


def persist_manual_session_event(
    db: OrmSession,
    session_id: int,
    data: SessionEventCreate,
    request_id: str | None,
) -> SessionEvent:
    """Crea un SessionEvent. El caller debe haber validado acceso a la sesión."""
    event_type = (data.event_type or "").strip()
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type requerido")
    payload = data.payload
    if isinstance(payload, dict) and request_id and "request_id" not in payload:
        payload = dict(payload)
        payload["request_id"] = request_id
    event = SessionEvent(
        session_id=session_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_session_events_ordered(db: OrmSession, session_id: int) -> list[SessionEvent]:
    """Eventos de una sesión ordenados por occurred_at. El caller debe haber validado acceso."""
    return db.query(SessionEvent).filter(SessionEvent.session_id == session_id).order_by(SessionEvent.occurred_at).all()
