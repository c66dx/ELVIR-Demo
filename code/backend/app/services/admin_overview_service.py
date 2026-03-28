"""Overview de jóvenes y profesionales (panel admin)."""
from __future__ import annotations

from typing import Literal

from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.schemas.admin import (
    AdminAssignedProfessional,
    AdminListMeta,
    AdminProfessionalRow,
    AdminUsersOverviewMeta,
    AdminUsersOverviewResponse,
    AdminYouthRow,
)
from app.services.admin_queries import (
    get_active_assignment_map_for_youths,
    get_last_login_map,
    get_pending_invitation_email_map,
    resolve_login_type,
)
from app.services.youth_queries import get_last_session_map


def build_users_overview(
    db: DBSession,
    *,
    tab: Literal["youths", "professionals"] | None,
    page: int | None,
    page_size: int | None,
    search: str | None,
) -> AdminUsersOverviewResponse:
    search_term = search.strip() if search else None
    use_pagination = bool(tab or page or page_size or search_term)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    youths: list[Youth] = []
    professionals: list[Professional] = []
    youths_total = 0
    professionals_total = 0

    if tab in (None, "youths"):
        youths_q = db.query(Youth)
        if search_term:
            like = f"%{search_term}%"
            youths_q = youths_q.outerjoin(User, Youth.user_id == User.id).filter(
                or_(
                    Youth.display_name.ilike(like),
                    Youth.identifier.ilike(like),
                    User.email.ilike(like),
                )
            )
        if use_pagination:
            youths_total = youths_q.order_by(None).count()
            offset = (page - 1) * page_size
            youths = youths_q.order_by(Youth.id.asc()).offset(offset).limit(page_size).all()
        else:
            youths = youths_q.order_by(Youth.id.asc()).all()

    if tab in (None, "professionals"):
        professionals_q = db.query(Professional)
        if search_term:
            like = f"%{search_term}%"
            professionals_q = professionals_q.outerjoin(User, Professional.user_id == User.id).filter(
                or_(
                    Professional.display_name.ilike(like),
                    User.email.ilike(like),
                )
            )
        if use_pagination:
            professionals_total = professionals_q.order_by(None).count()
            offset = (page - 1) * page_size
            professionals = professionals_q.order_by(Professional.id.asc()).offset(offset).limit(page_size).all()
        else:
            professionals = professionals_q.order_by(Professional.id.asc()).all()

    youth_ids = [y.id for y in youths]
    user_ids = [y.user_id for y in youths if y.user_id] + [p.user_id for p in professionals if p.user_id]

    user_rows = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map: dict[int, User] = {u.id: u for u in user_rows}
    last_login_map = get_last_login_map(db, user_ids) if user_ids else {}
    last_session_map = get_last_session_map(db, youth_ids) if youth_ids else {}
    assignment_map = get_active_assignment_map_for_youths(db, youth_ids) if youth_ids else {}
    invitation_email_map = get_pending_invitation_email_map(db, youth_ids) if youth_ids else {}

    professional_ids = [a.professional_id for a in assignment_map.values()]
    prof_rows = db.query(Professional).filter(Professional.id.in_(professional_ids)).all() if professional_ids else []
    prof_map = {p.id: p for p in prof_rows}

    youth_rows: list[AdminYouthRow] = []
    for y in youths:
        user = user_map.get(y.user_id) if y.user_id else None
        email = None
        if y.login_enabled and y.user_id and user and user.is_active:
            email = user.email
        elif not y.user_id:
            email = invitation_email_map.get(y.id)
        profile_photo_url = None
        if y.photo_url:
            profile_photo_url = y.photo_url
        elif user and user.profile_photo_url:
            profile_photo_url = user.profile_photo_url
        last_login_at = last_login_map.get(y.user_id) if y.user_id else None
        last_session = last_session_map.get(y.id)
        assignment = assignment_map.get(y.id)
        assigned_professional = None
        if assignment:
            prof = prof_map.get(assignment.professional_id)
            if prof:
                prof_user = user_map.get(prof.user_id)
                assigned_professional = AdminAssignedProfessional(
                    id=prof.id,
                    display_name=prof.display_name,
                    email=prof_user.email if prof_user else None,
                    is_active=prof.is_active,
                )
        youth_rows.append(
            AdminYouthRow(
                id=y.id,
                user_id=y.user_id,
                display_name=y.display_name,
                identifier=y.identifier,
                rut=y.rut,
                email=email,
                profile_photo_url=profile_photo_url,
                login_enabled=y.login_enabled,
                is_active=y.is_active,
                login_type=resolve_login_type(bool(email)),
                last_login_at=last_login_at,
                last_interview_at=last_session.started_at if last_session else None,
                last_interview_status=last_session.status if last_session else None,
                last_interview_mode=last_session.mode if last_session else None,
                assigned_professional=assigned_professional,
            )
        )

    professional_rows: list[AdminProfessionalRow] = []
    for p in professionals:
        user = user_map.get(p.user_id)
        email = user.email if user and user.is_active else None
        professional_rows.append(
            AdminProfessionalRow(
                id=p.id,
                user_id=p.user_id,
                display_name=p.display_name,
                email=email,
                profile_photo_url=user.profile_photo_url if user else None,
                is_active=p.is_active,
                login_type=resolve_login_type(bool(email)),
                last_login_at=last_login_map.get(p.user_id),
            )
        )

    meta = None
    if use_pagination:
        meta = AdminUsersOverviewMeta()
        if tab in (None, "youths"):
            meta.youths = AdminListMeta(total=youths_total, page=page, page_size=page_size)
        if tab in (None, "professionals"):
            meta.professionals = AdminListMeta(total=professionals_total, page=page, page_size=page_size)

    return AdminUsersOverviewResponse(youths=youth_rows, professionals=professional_rows, meta=meta)
