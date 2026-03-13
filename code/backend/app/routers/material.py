"""Router de material de apoyo."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.support_material import SupportMaterial
from app.models.material_suggestion import MaterialSuggestion
from app.models.material_view import MaterialView
from app.models.user import User
from app.models.youth import Youth
from app.models.professional import Professional
from app.models.assignment import Assignment
from app.schemas.material import CreateMaterialRequest, SuggestMaterialRequest, RecordViewRequest
from app.core.dependencies import get_current_user, get_current_professional, get_current_admin

router = APIRouter(tags=["material"])


def _support_material_to_dict(m: SupportMaterial) -> dict:
    """Convierte SupportMaterial a dict para respuesta JSON."""
    return {
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "type": m.type,
        "url": m.url,
        "job_role_id": m.job_role_id,
        "case_id": m.case_id,
        "created_by": getattr(m, "created_by", None),
        "active": m.active,
    }


@router.post("/support-material")
def create_support_material(
    data: CreateMaterialRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea material. Admin: material general (created_by=null). Profesional: material propio."""
    created_by = None
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            created_by = prof.id
    elif user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    m = SupportMaterial(
        title=data.title,
        description=data.description,
        type=data.type,
        url=data.url,
        job_role_id=data.job_role_id,
        case_id=data.case_id,
        created_by=created_by,
        active=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _support_material_to_dict(m)


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
    q = db.query(SupportMaterial).filter(SupportMaterial.active == True)
    if job_role_id:
        q = q.filter((SupportMaterial.job_role_id == job_role_id) | (SupportMaterial.job_role_id.is_(None)))
    if case_id:
        q = q.filter((SupportMaterial.case_id == case_id) | (SupportMaterial.case_id.is_(None)))
    # Profesional ve material general (created_by null) + su material propio
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            q = q.filter(
                (SupportMaterial.created_by.is_(None)) | (SupportMaterial.created_by == prof.id)
            )
    # JOVEN ve material general + material de profesionales que lo tienen asignado (vía sugerencias)
    # Por simplicidad MVP: joven ve todo el material activo (el filtro real sería por sugerencias)
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(SupportMaterial.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(SupportMaterial.id.desc()).all() if not use_pagination else q.all()
    return [_support_material_to_dict(m) for m in items]


@router.post("/support-material/suggest")
def suggest_material(
    data: SuggestMaterialRequest,
    prof=Depends(get_current_professional),
    db: Session = Depends(get_db),
):
    """Sugiere material a un joven asignado. Crea MATERIAL_SUGGESTIONS."""
    assign = db.query(Assignment).filter(
        Assignment.youth_id == data.youth_id,
        Assignment.professional_id == prof.id,
        Assignment.status == "ACTIVO",
    ).first()
    if not assign:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    sugg = MaterialSuggestion(
        youth_id=data.youth_id,
        material_id=data.material_id,
        professional_id=prof.id,
        session_id=data.session_id,
        reason=data.reason,
    )
    db.add(sugg)
    db.commit()
    db.refresh(sugg)
    return {
        "id": sugg.id,
        "youth_id": sugg.youth_id,
        "material_id": sugg.material_id,
        "professional_id": sugg.professional_id,
        "session_id": sugg.session_id,
        "reason": sugg.reason,
        "suggested_at": sugg.suggested_at.isoformat(),
    }


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
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id != youth_id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
    else:
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            assign = db.query(Assignment).filter(
                Assignment.youth_id == youth_id,
                Assignment.professional_id == prof.id,
                Assignment.status == "ACTIVO",
            ).first()
            if not assign:
                raise HTTPException(status_code=403, detail="Acceso denegado")
    q = (
        db.query(MaterialSuggestion, SupportMaterial)
        .outerjoin(SupportMaterial, MaterialSuggestion.material_id == SupportMaterial.id)
        .filter(MaterialSuggestion.youth_id == youth_id)
    )
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(MaterialSuggestion.suggested_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(MaterialSuggestion.suggested_at.desc()).all() if not use_pagination else q.all()
    return [
        {
            "id": m.id,
            "material_id": m.material_id,
            "professional_id": m.professional_id,
            "session_id": m.session_id,
            "reason": m.reason,
            "suggested_at": m.suggested_at.isoformat(),
            "material": _support_material_to_dict(mat) if mat else None,
        }
        for m, mat in items
    ]


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
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id != youth_id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
    else:
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            assign = db.query(Assignment).filter(
                Assignment.youth_id == youth_id,
                Assignment.professional_id == prof.id,
                Assignment.status == "ACTIVO",
            ).first()
            if not assign:
                raise HTTPException(status_code=403, detail="Acceso denegado")
    q = db.query(MaterialView).filter(MaterialView.youth_id == youth_id)
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Page"] = str(page)
            response.headers["X-Page-Size"] = str(page_size)
        q = q.order_by(MaterialView.seen_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(MaterialView.seen_at.desc()).all() if not use_pagination else q.all()
    return [{"id": m.id, "youth_id": m.youth_id, "material_id": m.material_id, "seen_at": m.seen_at.isoformat()} for m in items]


@router.post("/support-material/{material_id}/view")
def record_material_view(
    material_id: int,
    data: RecordViewRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra que un joven vio un material. Crea MATERIAL_VIEWS."""
    youth_id = data.youth_id
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id != youth_id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
    view = MaterialView(youth_id=youth_id, material_id=material_id)
    db.add(view)
    db.commit()
    db.refresh(view)
    return {"id": view.id, "youth_id": view.youth_id, "material_id": view.material_id, "seen_at": view.seen_at.isoformat()}

