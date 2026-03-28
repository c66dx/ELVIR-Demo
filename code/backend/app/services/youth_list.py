"""Listado de jóvenes con última sesión y cabeceras de paginación."""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DBSession

from app.models.assignment import Assignment
from app.models.user import User
from app.models.youth import Youth
from app.schemas.youth import LastSessionInfo, YouthWithLastSession, parse_profile_checklist
from app.services.youth_queries import get_last_session_map, get_user_email_map, get_user_profile_photo_map


@dataclass(frozen=True)
class YouthListResult:
    items: list[YouthWithLastSession]
    pagination_headers: dict[str, str] | None = None


def list_youths_with_last_session(
    db: DBSession,
    user: User,
    *,
    search: str | None,
    is_active: bool | None,
    login_enabled: bool | None,
    page: int | None,
    page_size: int | None,
) -> YouthListResult:
    """Lista jóvenes según rol, filtros y paginación. Cabeceras solo si aplica paginación."""
    if not isinstance(page, int):
        page = None
    if not isinstance(page_size, int):
        page_size = None

    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return YouthListResult(items=[])
        q = (
            db.query(Youth)
            .join(Assignment, Assignment.youth_id == Youth.id)
            .filter(Assignment.professional_id == prof.id, Assignment.status == "ACTIVO")
        )
    elif user.role == "ADMIN":
        q = db.query(Youth)
    else:
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        youths = [youth] if youth else []
        q = None

    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    pagination_headers: dict[str, str] | None = None

    if q is not None:
        if is_active is not None:
            q = q.filter(Youth.is_active == is_active)
        if login_enabled is not None:
            q = q.filter(Youth.login_enabled == login_enabled)
        if search and search.strip():
            term = f"%{search.strip()}%"
            cleaned = re.sub(r"[^0-9kK]", "", search).upper()
            conditions = [
                Youth.display_name.ilike(term),
                Youth.identifier.ilike(term),
                Youth.rut.ilike(term),
            ]
            if cleaned:
                rut_norm = func.replace(func.replace(func.upper(Youth.rut), ".", ""), "-", "")
                conditions.append(rut_norm.ilike(f"%{cleaned}%"))
            q = q.filter(or_(*conditions))
        if use_pagination:
            total = q.order_by(None).count()
            pagination_headers = {
                "X-Total-Count": str(total),
                "X-Page": str(page),
                "X-Page-Size": str(page_size),
            }
            q = q.order_by(Youth.id.asc()).offset((page - 1) * page_size).limit(page_size)
        youths = q.order_by(Youth.id.asc()).all() if not use_pagination else q.all()
    elif use_pagination:
        pagination_headers = {
            "X-Total-Count": str(len(youths)),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }

    youth_ids = [y.id for y in youths]
    user_ids = [y.user_id for y in youths if y.user_id]
    last_session_map = get_last_session_map(db, youth_ids)
    email_map = get_user_email_map(db, user_ids)
    photo_map = get_user_profile_photo_map(db, user_ids)

    result: list[YouthWithLastSession] = []
    for y in youths:
        last_sess = last_session_map.get(y.id)
        status_label = "Con sesiones" if last_sess else "Sin sesiones"
        last_session = None
        if last_sess:
            last_session = LastSessionInfo(
                id=last_sess.id,
                started_at=last_sess.started_at,
                status=last_sess.status,
                ended_at=last_sess.ended_at,
            )
        email = email_map.get(y.user_id) if y.user_id else None
        profile_photo_url = photo_map.get(y.user_id) if y.user_id else None
        final_photo_url = y.photo_url or profile_photo_url
        result.append(
            YouthWithLastSession(
                id=y.id,
                user_id=y.user_id,
                display_name=y.display_name,
                identifier=y.identifier,
                rut=y.rut,
                email=email,
                profile_photo_url=final_photo_url,
                phone=y.phone,
                year_of_birth=y.year_of_birth,
                diagnosis=y.diagnosis,
                login_enabled=y.login_enabled,
                is_active=y.is_active,
                general_notes=y.general_notes,
                profile_checklist=parse_profile_checklist(y.profile_checklist) or None,
                status_label=status_label,
                last_session=last_session,
            )
        )
    return YouthListResult(items=result, pagination_headers=pagination_headers)
