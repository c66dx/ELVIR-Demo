"""Creación de sesiones de simulación."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session as OrmSession

from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.user import User
from app.schemas.session import SessionCreate
from app.services.session_access import check_youth_access


def create_session_record(
    db: OrmSession,
    user: User,
    data: SessionCreate,
    request_id: str,
) -> SessionModel:
    """Crea sesión EN_CURSO y evento CREATED. Lanza HTTPException si las reglas de negocio fallan."""
    if not check_youth_access(db, user, data.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado al joven")

    professional_id = data.professional_id
    if data.mode == "SUPERVISADA":
        if user.role != "PROFESIONAL":
            raise HTTPException(status_code=403, detail="Solo profesionales pueden crear sesiones supervisadas")
        prof = db.query(Professional).filter(Professional.user_id == user.id, Professional.is_active == True).first()
        if not prof:
            raise HTTPException(status_code=403, detail="Acceso denegado: profesional no encontrado")
        if professional_id is None:
            professional_id = prof.id
        elif professional_id != prof.id:
            raise HTTPException(status_code=403, detail="professional_id no coincide con el profesional autenticado")
    else:
        if professional_id is not None:
            raise HTTPException(status_code=400, detail="professional_id no permitido en sesiones autogestionadas")
        professional_id = None

    session = SessionModel(
        youth_id=data.youth_id,
        professional_id=professional_id,
        simulation_template_id=data.simulation_template_id,
        mode=data.mode,
        status="EN_CURSO",
        last_heartbeat_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()
    db.add(
        SessionEvent(
            session_id=session.id,
            event_type="CREATED",
            payload={"source": "backend", "request_id": request_id},
        )
    )
    db.commit()
    db.refresh(session)
    return session
