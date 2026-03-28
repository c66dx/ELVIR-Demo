"""Router de administración: control de usuarios y logs."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.schemas.admin import AdminUsersOverviewResponse, AdminYouthLogsResponse, AuditLogListResponse
from app.services.admin_audit_service import build_audit_log_list_response
from app.services.admin_operations import (
    apply_admin_soft_delete_professional,
    apply_admin_soft_delete_youth,
    apply_hard_delete_youth,
)
from app.services.admin_overview_service import build_users_overview
from app.services.admin_youth_logs_service import build_youth_logs_response

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users/overview", response_model=AdminUsersOverviewResponse)
def get_users_overview(
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    tab: Literal["youths", "professionals"] | None = Query(None),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    search: str | None = Query(None, min_length=1),
):
    return build_users_overview(db, tab=tab, page=page, page_size=page_size, search=search)


@router.delete("/youths/{youth_id}")
def admin_delete_youth(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_admin_soft_delete_youth(db, youth_id)


@router.delete("/professionals/{professional_id}")
def admin_delete_professional(
    professional_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_admin_soft_delete_professional(db, professional_id)


@router.get("/youths/{youth_id}/logs", response_model=AdminYouthLogsResponse)
def admin_get_youth_logs(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    platform_page: int | None = Query(None, ge=1),
    platform_page_size: int | None = Query(None, ge=1, le=200),
    interviews_page: int | None = Query(None, ge=1),
    interviews_page_size: int | None = Query(None, ge=1, le=200),
):
    """Devuelve logs históricos del joven: accesos (platform_sessions) y sesiones de entrevista."""
    return build_youth_logs_response(
        db,
        youth_id,
        platform_page=platform_page,
        platform_page_size=platform_page_size,
        interviews_page=interviews_page,
        interviews_page_size=interviews_page_size,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    search: str | None = Query(None, min_length=1),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    status_code: int | None = Query(None, ge=100, le=599),
    actor_user_id: int | None = Query(None, ge=1),
    method: str | None = Query(None),
):
    page = page or 1
    page_size = page_size or 50
    search_term = search.strip() if search else None
    action_term = action.strip().lower() if action else None
    entity_term = entity_type.strip().lower() if entity_type else None
    method_term = method.strip().upper() if method else None

    return build_audit_log_list_response(
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


@router.delete("/youths/{youth_id}/hard")
def admin_hard_delete_youth(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_hard_delete_youth(db, youth_id)
