"""Consultas auxiliares y efectos sobre jóvenes (sesiones, usuarios, invitaciones)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session as SessionModel
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation


def get_last_session_map(db: DBSession, youth_ids: list[int]) -> dict[int, SessionModel]:
    """Última sesión por joven (evita N+1)."""
    if not youth_ids:
        return {}

    latest_per_youth = (
        db.query(
            SessionModel.youth_id.label("youth_id"),
            func.max(SessionModel.started_at).label("max_started_at"),
        )
        .filter(SessionModel.youth_id.in_(youth_ids))
        .group_by(SessionModel.youth_id)
        .subquery()
    )

    sessions = (
        db.query(SessionModel)
        .join(
            latest_per_youth,
            and_(
                SessionModel.youth_id == latest_per_youth.c.youth_id,
                SessionModel.started_at == latest_per_youth.c.max_started_at,
            ),
        )
        .order_by(SessionModel.youth_id.asc(), SessionModel.started_at.desc(), SessionModel.id.desc())
        .all()
    )

    by_youth: dict[int, SessionModel] = {}
    for s in sessions:
        if s.youth_id not in by_youth:
            by_youth[s.youth_id] = s
    return by_youth


def get_user_email_map(db: DBSession, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    users = db.query(User.id, User.email, User.is_active).filter(User.id.in_(user_ids)).all()
    return {u[0]: u[1] for u in users if u[2]}


def get_user_profile_photo_map(db: DBSession, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    users = db.query(User.id, User.profile_photo_url).filter(User.id.in_(user_ids)).all()
    return {u[0]: u[1] for u in users if u[1]}


def disable_youth_login(db: DBSession, youth: Youth) -> None:
    """Deshabilita login: desactiva usuario y libera email para reutilizar."""
    if youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user:
            user.is_active = False
            user.email = f"disabled+{user.id}@invalid.local"
    now = datetime.now(UTC)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )


def get_youth_email(db: DBSession, user_id: int) -> str | None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user.email


def get_user_profile_photo(db: DBSession, user_id: int) -> str | None:
    user = db.query(User).filter(User.id == user_id).first()
    return user.profile_photo_url if user else None


def get_pending_invitation_email(db: DBSession, youth_id: int) -> str | None:
    inv = (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth_id, YouthInvitation.used_at.is_(None))
        .order_by(desc(YouthInvitation.created_at))
        .first()
    )
    return inv.email if inv else None
