"""Consulta paginada de audit logs (panel admin)."""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import AdminListMeta, AuditLogListResponse, AuditLogRow


def fetch_audit_log_rows(
    db: DBSession,
    *,
    page: int,
    page_size: int,
    search_term: str | None,
    action_term: str | None,
    entity_term: str | None,
    status_code: int | None,
    actor_user_id: int | None,
    method_term: str | None,
) -> tuple[list[tuple[AuditLog, str | None]], int]:
    q = db.query(AuditLog, User.email).outerjoin(User, AuditLog.actor_user_id == User.id)

    if action_term:
        q = q.filter(AuditLog.action == action_term)
    if entity_term:
        q = q.filter(AuditLog.entity_type == entity_term)
    if status_code:
        q = q.filter(AuditLog.status_code == status_code)
    if actor_user_id:
        q = q.filter(AuditLog.actor_user_id == actor_user_id)
    if method_term:
        q = q.filter(AuditLog.method == method_term)
    if search_term:
        like = f"%{search_term}%"
        q = q.filter(
            or_(
                AuditLog.request_id.ilike(like),
                AuditLog.entity_id.ilike(like),
                AuditLog.path.ilike(like),
                User.email.ilike(like),
            )
        )

    total = q.order_by(None).count()
    rows = (
        q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def build_audit_log_list_response(
    db: DBSession,
    *,
    page: int,
    page_size: int,
    search_term: str | None,
    action_term: str | None,
    entity_term: str | None,
    status_code: int | None,
    actor_user_id: int | None,
    method_term: str | None,
) -> AuditLogListResponse:
    rows, total = fetch_audit_log_rows(
        db,
        page=page,
        page_size=page_size,
        search_term=search_term,
        action_term=action_term,
        entity_term=entity_term,
        status_code=status_code,
        actor_user_id=actor_user_id,
        method_term=method_term,
    )
    items = [
        AuditLogRow(
            id=log.id,
            request_id=log.request_id,
            actor_user_id=log.actor_user_id,
            actor_role=log.actor_role,
            actor_email=email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            status_code=log.status_code,
            method=log.method,
            path=log.path,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log, email in rows
    ]
    return AuditLogListResponse(
        items=items,
        meta=AdminListMeta(total=total, page=page, page_size=page_size),
    )
