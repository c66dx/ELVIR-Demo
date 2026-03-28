"""Router de profesionales (gestión por Admin)."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.professional import (
    ProfessionalCreate,
    ProfessionalCreateResponse,
    ProfessionalResponse,
    ProfessionalUpdate,
)
from app.core.dependencies import get_current_admin, get_current_user
from app.services.professional_access import assert_can_access_professional
from app.services.professional_service import (
    create_professional_with_invitation,
    fetch_professional_assignments,
    get_professional_by_id,
    get_user_by_id,
    professional_response_dict,
    query_professionals_admin,
    update_professional_admin,
    user_map_by_ids,
)

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.get("/{professional_id}/assignments")
def list_professional_assignments(
    professional_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista asignaciones de un profesional. Solo el propio profesional o Admin."""
    assert_can_access_professional(user, professional_id, db)
    rows, pagination_headers = fetch_professional_assignments(db, professional_id, page, page_size)
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    return rows


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    is_active: bool | None = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista todos los profesionales. Solo Admin."""
    profs, pagination_headers = query_professionals_admin(db, is_active, page, page_size)
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    user_ids = [p.user_id for p in profs]
    user_map = user_map_by_ids(db, user_ids)
    return [
        ProfessionalResponse(**professional_response_dict(p, user_map.get(p.user_id)))
        for p in profs
    ]


@router.post("", response_model=ProfessionalCreateResponse)
def create_professional(
    data: ProfessionalCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Crea un nuevo profesional. Solo Admin."""
    prof, user, activation_url = create_professional_with_invitation(
        db,
        email=data.email,
        display_name=data.display_name,
        specialty=data.specialty,
        institution=data.institution,
        app_base_url=settings.APP_BASE_URL,
    )
    return ProfessionalCreateResponse(
        **professional_response_dict(prof, user),
        activation_url=activation_url,
    )


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(
    professional_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle de un profesional. Admin o el propio profesional."""
    assert_can_access_professional(user, professional_id, db)
    prof = get_professional_by_id(db, professional_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    linked_user = get_user_by_id(db, prof.user_id)
    return ProfessionalResponse(**professional_response_dict(prof, linked_user))


@router.put("/{professional_id}", response_model=ProfessionalResponse)
def update_professional(
    professional_id: int,
    data: ProfessionalUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Actualiza datos de perfil de un profesional (no credenciales). Solo Admin."""
    prof, linked_user = update_professional_admin(
        db,
        professional_id,
        data.display_name,
        data.specialty,
        data.institution,
        data.is_active,
    )
    return ProfessionalResponse(**professional_response_dict(prof, linked_user))
