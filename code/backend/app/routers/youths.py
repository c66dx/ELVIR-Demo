"""Router de jóvenes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.user import User
from app.schemas.youth import YouthCreate, YouthUpdate, YouthResponse, YouthWithLastSession, YouthChangeEmailRequest
from app.schemas.platform_session import PlatformSessionResponse
from app.schemas.notification import YouthNotificationResponse, NotificationReadRequest
from app.core.dependencies import get_current_user, get_current_professional
from app.services.session_access import check_youth_access
from app.services.youth_photo import persist_youth_photo_upload
from app.services.youth_create_service import create_youth_for_professional
from app.services.youth_update_service import (
    activate_youth_for_professional,
    change_youth_email_for_professional,
    deactivate_youth_for_professional,
    update_youth_profile,
)
from app.services.youth_list import list_youths_with_last_session
from app.services.youth_lookup import lookup_youth_profiles, parse_lookup_ids
from app.services.youth_response import youth_to_response, youth_to_response_with_contact
from app.services.youth_platform_sessions import fetch_youth_platform_sessions
from app.services.youth_notifications import (
    fetch_youth_notifications,
    mark_all_youth_notifications_read,
    mark_youth_notifications_read,
)
from app.services.youth_access import (
    ensure_youth_photo_upload_access,
    ensure_youth_read_access,
    load_youth_or_404,
)

router = APIRouter(prefix="/youths", tags=["youths"])


class YouthLookupRequest(BaseModel):
    ids: list[int]


@router.get("", response_model=list[YouthWithLastSession])
def list_youths(
    search: str | None = None,
    is_active: bool | None = None,
    login_enabled: bool | None = None,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
):
    """Lista jóvenes. PROFESIONAL: asignados. JOVEN: solo su propio perfil.
    Filtros: search (nombre/identificador), is_active, login_enabled."""
    result = list_youths_with_last_session(
        db,
        user,
        search=search,
        is_active=is_active,
        login_enabled=login_enabled,
        page=page,
        page_size=page_size,
    )
    if result.pagination_headers and response:
        for key, value in result.pagination_headers.items():
            response.headers[key] = value
    return result.items


@router.post("/lookup")
def lookup_youths(
    data: YouthLookupRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Lookup rápido de nombres por ID, respetando permisos."""
    ids = parse_lookup_ids(data.ids)
    return lookup_youth_profiles(db, user, ids)


@router.post("", response_model=YouthResponse)
def create_youth(
    data: YouthCreate,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Crea joven y asignación automática. identifier lo genera el sistema. Si login_enabled+email: genera invitación."""
    youth, activation_url = create_youth_for_professional(db, data, prof)
    return youth_to_response(youth, activation_url)


@router.get("/{youth_id}", response_model=YouthResponse)
def get_youth(
    youth_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Obtiene perfil de joven. Requiere ser el propio joven o profesional asignado."""
    youth = load_youth_or_404(db, youth_id)
    ensure_youth_read_access(db, user, youth)
    return youth_to_response_with_contact(db, youth, include_pending_invitation_email=True)


@router.post("/{youth_id}/photo", response_model=YouthResponse)
def upload_youth_photo(
    youth_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Sube foto del joven (profesional asignado o el propio joven)."""
    youth = load_youth_or_404(db, youth_id)
    ensure_youth_photo_upload_access(db, user, youth)
    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    persist_youth_photo_upload(db, youth, file, base)
    return youth_to_response_with_contact(db, youth, include_pending_invitation_email=True)


@router.get("/{youth_id}/platform-sessions", response_model=list[PlatformSessionResponse])
def list_youth_platform_sessions(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
):
    """Lista entradas/salidas del joven a la plataforma (login/logout). Solo si tiene user_id."""
    youth = load_youth_or_404(db, youth_id)
    ensure_youth_read_access(db, user, youth)
    if not youth.user_id:
        return []
    sessions, pagination_headers = fetch_youth_platform_sessions(
        db, youth.user_id, page, page_size
    )
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    return [PlatformSessionResponse.model_validate(s) for s in sessions]


@router.put("/{youth_id}", response_model=YouthResponse)
def update_youth(
    youth_id: int,
    data: YouthUpdate,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Actualiza perfil de joven. Si habilita login sin user_id: genera nueva invitación."""
    youth, activation_url = update_youth_profile(db, youth_id, prof, data)
    return youth_to_response_with_contact(db, youth, activation_url=activation_url)


@router.patch("/{youth_id}/deactivate", response_model=YouthResponse)
def deactivate_youth(
    youth_id: int,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Desactiva joven (soft delete). Solo profesional asignado."""
    youth = deactivate_youth_for_professional(db, youth_id, prof)
    return youth_to_response_with_contact(db, youth)


@router.post("/{youth_id}/change-email", response_model=YouthResponse)
def change_youth_email(
    youth_id: int,
    data: YouthChangeEmailRequest,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Cambia el email del joven y genera nuevo enlace de activación. Requiere login habilitado."""
    youth, activation_url = change_youth_email_for_professional(db, youth_id, prof, data)
    return youth_to_response_with_contact(db, youth, activation_url=activation_url)


@router.patch("/{youth_id}/activate", response_model=YouthResponse)
def activate_youth(
    youth_id: int,
    prof=Depends(get_current_professional),
    db: DBSession = Depends(get_db),
):
    """Reactiva joven. Solo profesional asignado."""
    youth = activate_youth_for_professional(db, youth_id, prof)
    return youth_to_response_with_contact(db, youth)


@router.get("/{youth_id}/notifications", response_model=list[YouthNotificationResponse])
def list_youth_notifications(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    unread_only: bool | None = Query(None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    response: Response = None,
):
    """Lista notificaciones del joven. JOVEN: solo propias. PROFESIONAL: si asignado. ADMIN: todo."""
    if not check_youth_access(db, user, youth_id, allow_admin=True):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    items, notification_headers = fetch_youth_notifications(
        db, youth_id, page, page_size, unread_only
    )
    if response:
        for key, value in notification_headers.items():
            response.headers[key] = value
    return items


@router.patch("/{youth_id}/notifications/read")
def mark_notifications_read(
    youth_id: int,
    data: NotificationReadRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Marca notificaciones como leídas (por IDs)."""
    if not check_youth_access(db, user, youth_id, allow_admin=True):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not data.ids:
        return {"updated": 0}
    updated = mark_youth_notifications_read(db, youth_id, data.ids)
    return {"updated": updated}


@router.patch("/{youth_id}/notifications/read-all")
def mark_all_notifications_read(
    youth_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Marca todas las notificaciones del joven como leídas."""
    if not check_youth_access(db, user, youth_id, allow_admin=True):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    updated = mark_all_youth_notifications_read(db, youth_id)
    return {"updated": updated}


