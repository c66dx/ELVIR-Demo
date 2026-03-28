"""Consultas auxiliares para el panel de administración (overview de usuarios)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func
from sqlalchemy.orm import Session as DBSession

from app.models.assignment import Assignment
from app.models.platform_session import PlatformSession
from app.models.youth_invitation import YouthInvitation


def get_last_login_map(db: DBSession, user_ids: list[int]) -> dict[int, datetime]:
    if not user_ids:
        return {}
    latest_per_user = (
        db.query(
            PlatformSession.user_id.label("user_id"),
            func.max(PlatformSession.started_at).label("max_started_at"),
        )
        .filter(PlatformSession.user_id.in_(user_ids))
        .group_by(PlatformSession.user_id)
        .subquery()
    )
    rows = (
        db.query(PlatformSession.user_id, PlatformSession.started_at)
        .join(
            latest_per_user,
            and_(
                PlatformSession.user_id == latest_per_user.c.user_id,
                PlatformSession.started_at == latest_per_user.c.max_started_at,
            ),
        )
        .all()
    )
    return {r[0]: r[1] for r in rows}


def get_active_assignment_map_for_youths(db: DBSession, youth_ids: list[int]) -> dict[int, Assignment]:
    if not youth_ids:
        return {}
    latest_per_youth = (
        db.query(
            Assignment.youth_id.label("youth_id"),
            func.max(Assignment.assigned_at).label("max_assigned_at"),
        )
        .filter(Assignment.status == "ACTIVO", Assignment.youth_id.in_(youth_ids))
        .group_by(Assignment.youth_id)
        .subquery()
    )
    assignments = (
        db.query(Assignment)
        .join(
            latest_per_youth,
            and_(
                Assignment.youth_id == latest_per_youth.c.youth_id,
                Assignment.assigned_at == latest_per_youth.c.max_assigned_at,
            ),
        )
        .all()
    )
    return {a.youth_id: a for a in assignments}


def get_pending_invitation_email_map(db: DBSession, youth_ids: list[int]) -> dict[int, str]:
    if not youth_ids:
        return {}
    latest_per_youth = (
        db.query(
            YouthInvitation.youth_id.label("youth_id"),
            func.max(YouthInvitation.created_at).label("max_created_at"),
        )
        .filter(YouthInvitation.youth_id.in_(youth_ids), YouthInvitation.used_at.is_(None))
        .group_by(YouthInvitation.youth_id)
        .subquery()
    )
    rows = (
        db.query(YouthInvitation.youth_id, YouthInvitation.email)
        .join(
            latest_per_youth,
            and_(
                YouthInvitation.youth_id == latest_per_youth.c.youth_id,
                YouthInvitation.created_at == latest_per_youth.c.max_created_at,
            ),
        )
        .all()
    )
    return {r[0]: r[1] for r in rows}


def resolve_login_type(has_email: bool) -> str:
    return "HABILITADO" if has_email else "NO_HABILITADO"
