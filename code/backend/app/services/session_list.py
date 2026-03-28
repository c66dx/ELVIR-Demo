"""Listado y filtrado de sesiones."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session as OrmSession

from app.models.session import Session as SessionModel
from app.models.user import User
from app.models.youth import Youth
from app.services.session_access import build_sessions_query, expire_stale_sessions


def fetch_sessions_list(
    db: OrmSession,
    user: User,
    youth_id: int | None,
    *,
    search: str | None,
    status: str | None,
    mode: str | None,
    start_date: date | None,
    end_date: date | None,
    page: int | None,
    page_size: int | None,
) -> tuple[list[SessionModel], tuple[int, int, int] | None]:
    """
    Devuelve sesiones y, si hay paginación, (total, page, page_size) para cabeceras HTTP.
    """
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
    else:
        page = 1
        page_size = 50

    expire_stale_sessions(db)

    sessions_q = build_sessions_query(db, user, youth_id)
    if sessions_q is None:
        if use_pagination:
            return [], (0, page, page_size)
        return [], None

    if search and search.strip():
        term = f"%{search.strip()}%"
        cleaned = re.sub(r"[^0-9kK]", "", search).upper()
        conditions = [
            Youth.display_name.ilike(term),
            Youth.rut.ilike(term),
            Youth.identifier.ilike(term),
        ]
        if cleaned:
            rut_norm = func.replace(func.replace(func.upper(Youth.rut), ".", ""), "-", "")
            conditions.append(rut_norm.ilike(f"%{cleaned}%"))
        sessions_q = sessions_q.join(Youth, Youth.id == SessionModel.youth_id).filter(or_(*conditions))

    if status:
        allowed_status = {"EN_CURSO", "COMPLETADA", "CANCELADA", "ERROR"}
        if status not in allowed_status:
            raise HTTPException(status_code=400, detail="Estado de sesión inválido")
        sessions_q = sessions_q.filter(SessionModel.status == status)

    if mode:
        allowed_modes = {"AUTOGESTIONADA", "SUPERVISADA"}
        if mode not in allowed_modes:
            raise HTTPException(status_code=400, detail="Modo de sesión inválido")
        sessions_q = sessions_q.filter(SessionModel.mode == mode)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="Rango de fechas inválido")

    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        sessions_q = sessions_q.filter(SessionModel.started_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        sessions_q = sessions_q.filter(SessionModel.started_at <= end_dt)

    if use_pagination:
        total = sessions_q.order_by(None).count()
        sessions_q = sessions_q.order_by(SessionModel.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    else:
        total = None
        sessions_q = sessions_q.order_by(SessionModel.started_at.desc())

    sessions = sessions_q.all()
    if use_pagination:
        return sessions, (total, page, page_size)
    return sessions, None


def apply_sessions_pagination_headers(
    response: Response | None,
    pag: tuple[int, int, int] | None,
) -> None:
    if pag and response is not None:
        total, p, ps = pag
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(p)
        response.headers["X-Page-Size"] = str(ps)
