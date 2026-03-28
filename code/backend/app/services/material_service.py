"""Consultas y persistencia de material de apoyo."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.material_suggestion import MaterialSuggestion
from app.models.material_view import MaterialView
from app.models.professional import Professional
from app.models.support_material import SupportMaterial
from app.models.user import User
from app.models.youth import Youth
from app.schemas.material import CreateMaterialRequest, SuggestMaterialRequest
from app.services.notifications import upsert_youth_notification


def support_material_to_dict(m: SupportMaterial) -> dict:
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


def create_support_material_record(
    db: Session,
    data: CreateMaterialRequest,
    created_by: int | None,
) -> SupportMaterial:
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
    return m


def fetch_support_material_list(
    db: Session,
    user: User,
    job_role_id: Optional[int],
    case_id: Optional[int],
    page: int | None,
    page_size: int | None,
) -> tuple[list[SupportMaterial], dict[str, str] | None]:
    q = db.query(SupportMaterial).filter(SupportMaterial.active == True)
    if job_role_id:
        q = q.filter((SupportMaterial.job_role_id == job_role_id) | (SupportMaterial.job_role_id.is_(None)))
    if case_id:
        q = q.filter((SupportMaterial.case_id == case_id) | (SupportMaterial.case_id.is_(None)))
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            q = q.filter(
                (SupportMaterial.created_by.is_(None)) | (SupportMaterial.created_by == prof.id)
            )
    elif user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth:
            return [], None
        suggested_ids = select(MaterialSuggestion.material_id).where(MaterialSuggestion.youth_id == youth.id)
        q = q.filter(
            or_(
                SupportMaterial.created_by.is_(None),
                SupportMaterial.id.in_(suggested_ids),
            )
        )

    use_pagination = bool(page or page_size)
    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(SupportMaterial.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(SupportMaterial.id.desc()).all() if not use_pagination else q.all()
    return items, pagination_headers


def assert_user_can_list_support_material(user: User) -> None:
    if user.role not in ("ADMIN", "PROFESIONAL", "JOVEN"):
        raise HTTPException(status_code=403, detail="Acceso denegado")


def resolve_created_by_for_support_material(db: Session, user: User) -> int | None:
    """Admin: material global. Profesional: id de profesional. Otros: 403."""
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        return prof.id if prof else None
    if user.role == "ADMIN":
        return None
    raise HTTPException(status_code=403, detail="Acceso denegado")


def create_support_material_from_user(db: Session, data: CreateMaterialRequest, user: User) -> SupportMaterial:
    created_by = resolve_created_by_for_support_material(db, user)
    return create_support_material_record(db, data, created_by)


def assert_youth_access_for_material_lists(db: Session, user: User, youth_id: int) -> None:
    """JOVEN: solo su ficha. PROFESIONAL: asignación ACTIVO. Admin u otros sin fila Prof: permitido (mismo criterio que el router)."""
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id != youth_id:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return
    prof = db.query(Professional).filter(Professional.user_id == user.id).first()
    if prof:
        assign = db.query(Assignment).filter(
            Assignment.youth_id == youth_id,
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        ).first()
        if not assign:
            raise HTTPException(status_code=403, detail="Acceso denegado")


def assert_youth_self_for_material_view(db: Session, user: User, youth_id: int) -> None:
    if user.role != "JOVEN":
        return
    youth = db.query(Youth).filter(Youth.user_id == user.id).first()
    if not youth or youth.id != youth_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")


def suggest_material_to_youth(
    db: Session,
    prof: Professional,
    data: SuggestMaterialRequest,
) -> dict:
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
    db.flush()
    material = db.query(SupportMaterial).filter(SupportMaterial.id == data.material_id).first()
    material_title = material.title if material else None
    message = (
        f'Tu tutor te asigno "{material_title}".'
        if material_title
        else "Tu tutor te asigno un material nuevo para revisar."
    )
    upsert_youth_notification(
        db,
        youth_id=data.youth_id,
        type="material",
        title="Material asignado",
        message=message,
        link="/joven/material",
        entity_type="material_suggestion",
        entity_id=sugg.id,
    )
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


def fetch_youth_material_suggestions(
    db: Session,
    youth_id: int,
    page: int | None,
    page_size: int | None,
) -> tuple[list[dict], dict[str, str] | None]:
    q = (
        db.query(MaterialSuggestion, SupportMaterial)
        .outerjoin(SupportMaterial, MaterialSuggestion.material_id == SupportMaterial.id)
        .filter(MaterialSuggestion.youth_id == youth_id)
    )
    use_pagination = bool(page or page_size)
    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(MaterialSuggestion.suggested_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(MaterialSuggestion.suggested_at.desc()).all() if not use_pagination else q.all()
    rows = [
        {
            "id": m.id,
            "material_id": m.material_id,
            "professional_id": m.professional_id,
            "session_id": m.session_id,
            "reason": m.reason,
            "suggested_at": m.suggested_at.isoformat(),
            "material": support_material_to_dict(mat) if mat else None,
        }
        for m, mat in items
    ]
    return rows, pagination_headers


def fetch_youth_material_views(
    db: Session,
    youth_id: int,
    page: int | None,
    page_size: int | None,
) -> tuple[list[dict], dict[str, str] | None]:
    q = db.query(MaterialView).filter(MaterialView.youth_id == youth_id)
    use_pagination = bool(page or page_size)
    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        page = page or 1
        page_size = page_size or 50
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(MaterialView.seen_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = q.order_by(MaterialView.seen_at.desc()).all() if not use_pagination else q.all()
    rows = [
        {"id": m.id, "youth_id": m.youth_id, "material_id": m.material_id, "seen_at": m.seen_at.isoformat()}
        for m in items
    ]
    return rows, pagination_headers


def record_youth_material_view(
    db: Session,
    material_id: int,
    youth_id: int,
) -> dict:
    view = MaterialView(youth_id=youth_id, material_id=material_id)
    db.add(view)
    db.commit()
    db.refresh(view)
    return {
        "id": view.id,
        "youth_id": view.youth_id,
        "material_id": view.material_id,
        "seen_at": view.seen_at.isoformat(),
    }
