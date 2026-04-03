"""Listado paginado de sesiones de plataforma (login/logout) por usuario."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession

from app.models.platform_session import PlatformSession


def fetch_youth_platform_sessions(
    db: DBSession,
    platform_user_id: int,
    page: int | None,
    page_size: int | None,
) -> tuple[list[PlatformSession], dict[str, str] | None]:
    """
    Devuelve sesiones de plataforma ordenadas por started_at descendente.
    Cabeceras de paginación solo si page o page_size están definidos.
    """
    q = db.query(PlatformSession).filter(PlatformSession.user_id == platform_user_id)
    use_pagination = bool(page or page_size)
    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(desc(PlatformSession.started_at)).offset((page - 1) * page_size).limit(page_size)
    sessions = q.order_by(desc(PlatformSession.started_at)).all() if not use_pagination else q.all()
    return sessions, pagination_headers
