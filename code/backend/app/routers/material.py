"""Router de material de apoyo."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.material import CreateMaterialRequest, SuggestMaterialRequest, RecordViewRequest
from app.core.dependencies import get_current_user, get_current_professional
from app.services.material_service import (
    assert_user_can_list_support_material,
    assert_youth_access_for_material_lists,
    assert_youth_self_for_material_view,
    create_support_material_from_user,
    fetch_support_material_list,
    fetch_youth_material_suggestions,
    fetch_youth_material_views,
    record_youth_material_view,
    suggest_material_to_youth,
    support_material_to_dict,
)

router = APIRouter(tags=["material"])


@router.post("/support-material")
def create_support_material(
    data: CreateMaterialRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea material. Admin: material general (created_by=nulo). Profesional: material propio."""
    m = create_support_material_from_user(db, data, user)
    return support_material_to_dict(m)


@router.get("/support-material")
def list_support_material(
    job_role_id: Optional[int] = Query(None),
    case_id: Optional[int] = Query(None),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista material activo. Filtros opcionales: job_role_id, case_id. Visibilidad por rol."""
    assert_user_can_list_support_material(user)
    items, pagination_headers = fetch_support_material_list(
        db, user, job_role_id, case_id, page, page_size
    )
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    return [support_material_to_dict(m) for m in items]


@router.post("/support-material/suggest")
def suggest_material(
    data: SuggestMaterialRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Sugiere material a un joven asignado. Crea MATERIAL_SUGGESTIONS."""
    return suggest_material_to_youth(db, prof, data)


@router.get("/youths/{youth_id}/material-suggestions")
def get_youth_material_suggestions(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista sugerencias de material para un joven. JOVEN: solo propias. PROFESIONAL: si asignado."""
    assert_youth_access_for_material_lists(db, user, youth_id)
    rows, pagination_headers = fetch_youth_material_suggestions(db, youth_id, page, page_size)
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    return rows


@router.get("/youths/{youth_id}/material-views")
def get_youth_material_views(
    youth_id: int,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Lista material visto por un joven. Requiere acceso al joven."""
    assert_youth_access_for_material_lists(db, user, youth_id)
    rows, pagination_headers = fetch_youth_material_views(db, youth_id, page, page_size)
    if pagination_headers and response:
        for key, value in pagination_headers.items():
            response.headers[key] = value
    return rows


@router.post("/support-material/{material_id}/view")
def record_material_view(
    material_id: int,
    data: RecordViewRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra que un joven vio un material. Crea MATERIAL_VIEWS."""
    assert_youth_self_for_material_view(db, user, data.youth_id)
    return record_youth_material_view(db, material_id, data.youth_id)
