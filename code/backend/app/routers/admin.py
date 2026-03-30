"""Router de administración: control de usuarios y logs."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.core.dependencies import get_current_admin
from app.core.limiter import limiter
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


@router.get(
    "/users/overview",
    response_model=AdminUsersOverviewResponse,
    summary="Resumen de usuarios (jóvenes / profesionales)",
)
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def get_users_overview(
    request: Request,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    tab: Annotated[Literal["youths", "professionals"] | None, Query()] = None,
    page: Annotated[int | None, Query(ge=1)] = None,
    page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
):
    return build_users_overview(db, tab=tab, page=page, page_size=page_size, search=search)


@router.delete("/youths/{youth_id}")
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def admin_delete_youth(
    request: Request,
    youth_id: Annotated[int, Path(ge=1)],
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_admin_soft_delete_youth(db, youth_id)


@router.delete("/professionals/{professional_id}")
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def admin_delete_professional(
    request: Request,
    professional_id: Annotated[int, Path(ge=1)],
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_admin_soft_delete_professional(db, professional_id)


@router.get("/youths/{youth_id}/logs", response_model=AdminYouthLogsResponse)
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def admin_get_youth_logs(
    request: Request,
    youth_id: Annotated[int, Path(ge=1)],
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    platform_page: Annotated[int | None, Query(ge=1)] = None,
    platform_page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    interviews_page: Annotated[int | None, Query(ge=1)] = None,
    interviews_page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
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
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def list_audit_logs(
    request: Request,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    page: Annotated[int | None, Query(ge=1)] = None,
    page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    action: Annotated[str | None, Query(max_length=120)] = None,
    entity_type: Annotated[str | None, Query(max_length=120)] = None,
    status_code: Annotated[int | None, Query(ge=100, le=599)] = None,
    actor_user_id: Annotated[int | None, Query(ge=1)] = None,
    method: Annotated[str | None, Query(max_length=16)] = None,
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
@limiter.limit(settings.ADMIN_API_RATE_LIMIT)
def admin_hard_delete_youth(
    request: Request,
    youth_id: Annotated[int, Path(ge=1)],
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    return apply_hard_delete_youth(db, youth_id)
