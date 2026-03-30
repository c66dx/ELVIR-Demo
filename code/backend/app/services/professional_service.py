"""Listado, alta y actualización de profesionales (Admin) y asignaciones paginadas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.professional_invitation import ProfessionalInvitation
from app.models.user import User


def fetch_professional_assignments(
    db: Session,
    professional_id: int,
    page: int | None,
    page_size: int | None,
) -> tuple[list[dict], dict[str, str] | None]:
    """Asignaciones de un profesional, opcionalmente paginadas; payload listo para JSON."""
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    q = db.query(Assignment).filter(Assignment.professional_id == professional_id)
    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(Assignment.assigned_at.desc()).offset((page - 1) * page_size).limit(page_size)
    else:
        q = q.order_by(Assignment.assigned_at.desc())

    items = q.all()
    rows = [
        {
            "id": a.id,
            "youth_id": a.youth_id,
            "professional_id": a.professional_id,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
        }
        for a in items
    ]
    return rows, pagination_headers


def query_professionals_admin(
    db: Session,
    is_active: bool | None,
    page: int | None,
    page_size: int | None,
) -> tuple[list[Professional], dict[str, str] | None]:
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    q = db.query(Professional)
    if is_active is not None:
        q = q.filter(Professional.is_active == is_active)

    pagination_headers: dict[str, str] | None = None
    if use_pagination:
        total = q.order_by(None).count()
        pagination_headers = {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Page-Size": str(page_size),
        }
        q = q.order_by(Professional.id).offset((page - 1) * page_size).limit(page_size)
    else:
        q = q.order_by(Professional.id)
    return q.all(), pagination_headers


def user_map_by_ids(db: Session, user_ids: list[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    rows = db.query(User).filter(User.id.in_(user_ids)).all()
    return {u.id: u for u in rows}


def professional_response_dict(prof: Professional, linked_user: User | None) -> dict:
    """Campos para ProfessionalResponse / ProfessionalCreateResponse (sin activation_url)."""
    return {
        "id": prof.id,
        "user_id": prof.user_id,
        "display_name": prof.display_name,
        "specialty": prof.specialty,
        "institution": prof.institution,
        "profile_photo_url": linked_user.profile_photo_url if linked_user else None,
        "is_active": prof.is_active,
        "created_at": prof.created_at,
        "updated_at": prof.updated_at,
    }


def create_professional_with_invitation(
    db: Session,
    *,
    email: str,
    display_name: str,
    specialty: str | None,
    institution: str | None,
    app_base_url: str,
) -> tuple[Professional, User, str]:
    """Crea User inactivo, Professional e invitación. Devuelve prof, user, activation_url."""
    existing = db.query(User).filter(User.email.ilike(email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    temp_password = uuid.uuid4().hex
    user = User(
        email=email.lower(),
        password_hash=get_password_hash(temp_password),
        role="PROFESIONAL",
        is_active=False,
    )
    db.add(user)
    db.flush()

    prof = Professional(
        user_id=user.id,
        display_name=display_name,
        specialty=specialty,
        institution=institution,
        is_active=True,
    )
    db.add(prof)
    db.flush()

    now = datetime.now(UTC)
    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    db.add(
        ProfessionalInvitation(
            professional_id=prof.id,
            email=user.email,
            token=token,
            expires_at=expires,
        )
    )
    db.commit()
    db.refresh(prof)

    activation_url = f"{app_base_url.rstrip('/')}/activar?token={token}"
    return prof, user, activation_url


def get_professional_by_id(db: Session, professional_id: int) -> Professional | None:
    return db.query(Professional).filter(Professional.id == professional_id).first()


def get_user_by_id(db: Session, user_id: int | None) -> User | None:
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def update_professional_admin(
    db: Session,
    professional_id: int,
    display_name: str,
    specialty: str | None,
    institution: str | None,
    is_active: bool | None,
) -> tuple[Professional, User | None]:
    prof = db.query(Professional).filter(Professional.id == professional_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    prof.display_name = display_name
    prof.specialty = specialty
    prof.institution = institution
    if is_active is not None:
        prof.is_active = is_active
        if prof.user_id:
            user = db.query(User).filter(User.id == prof.user_id).first()
            if user:
                user.is_active = is_active
    db.commit()
    db.refresh(prof)
    linked_user = db.query(User).filter(User.id == prof.user_id).first() if prof.user_id else None
    return prof, linked_user
