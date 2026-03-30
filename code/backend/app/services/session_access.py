"""Acceso a datos de jóvenes/sesiones y expiración de sesiones inactivas (compartido entre routers)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_event import SessionEvent
from app.models.user import User
from app.models.youth import Youth


def _dt_utc(dt: datetime) -> datetime:
    """SQLite puede devolver datetimes naive; normaliza a UTC para aritmética con now."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def check_youth_access(
    db: Session,
    user: User,
    youth_id: int,
    *,
    allow_admin: bool = False,
) -> bool:
    """Verifica si el usuario puede acceder al joven (propio o asignado; opcionalmente admin)."""
    if allow_admin and user.role == "ADMIN":
        return True
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        return bool(youth and youth.id == youth_id)
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return False
        assign = (
            db.query(Assignment)
            .filter(
                Assignment.youth_id == youth_id,
                Assignment.professional_id == prof.id,
                Assignment.status == "ACTIVO",
            )
            .first()
        )
        return assign is not None
    return False


def expire_stale_sessions(db: Session) -> int:
    """Cancela sesiones EN_CURSO sin heartbeat reciente."""
    timeout_minutes = getattr(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 0) or 0
    if timeout_minutes <= 0:
        return 0
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=timeout_minutes)
    stale_q = db.query(SessionModel).filter(
        SessionModel.status == "EN_CURSO",
        or_(
            SessionModel.last_heartbeat_at < cutoff,
            and_(
                SessionModel.last_heartbeat_at.is_(None),
                SessionModel.started_at < cutoff,
            ),
        ),
    )
    stale_sessions = stale_q.all()
    if not stale_sessions:
        return 0
    for session in stale_sessions:
        session.status = "CANCELADA"
        session.ended_at = now
        metrics = dict(session.metrics) if session.metrics else {}
        metrics["motivo"] = "ABANDONO_TIMEOUT"
        metrics["auto_cancelled"] = True
        metrics["idle_timeout_minutes"] = timeout_minutes
        session.metrics = metrics
        if session.started_at:
            session.duration_seconds = int((now - _dt_utc(session.started_at)).total_seconds())
        db.add(
            SessionEvent(
                session_id=session.id,
                event_type="AUTO_CANCELLED",
                payload={"motivo": "ABANDONO_TIMEOUT", "idle_timeout_minutes": timeout_minutes},
            )
        )
    db.commit()
    return len(stale_sessions)


def build_sessions_query(db: Session, user: User, youth_id: int | None):
    """Construye query base de sesiones según rol y filtros de acceso."""
    if youth_id:
        if not check_youth_access(db, user, youth_id, allow_admin=False):
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return db.query(SessionModel).filter(SessionModel.youth_id == youth_id)

    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth:
            return None
        return db.query(SessionModel).filter(SessionModel.youth_id == youth.id)

    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return None
        youth_ids_subq = select(Assignment.youth_id).where(
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        )
        return db.query(SessionModel).filter(SessionModel.youth_id.in_(youth_ids_subq))

    return None


def require_session_access(db: Session, session_id: int, user: User) -> SessionModel:
    """Carga la sesión por id o 404; comprueba acceso al joven o 403."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return session


def require_session_for_start(db: Session, session_id: int, user: User) -> SessionModel:
    """Para POST /start: 404, luego 409 si no está EN_CURSO, luego 403 sin acceso."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status != "EN_CURSO":
        raise HTTPException(status_code=409, detail="Sesión ya cerrada")
    if not check_youth_access(db, user, session.youth_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return session


def touch_session_heartbeat(db: Session, session_id: int, user: User) -> dict:
    """Actualiza last_heartbeat_at si la sesión está EN_CURSO."""
    session = require_session_access(db, session_id, user)
    if session.status != "EN_CURSO":
        return {"ok": False, "status": session.status}
    session.last_heartbeat_at = datetime.now(UTC)
    db.commit()
    return {"ok": True}
