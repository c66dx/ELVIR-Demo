"""Actualización de perfil de jóvenes por profesional asignado."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.schemas.youth import YouthChangeEmailRequest, YouthUpdate
from app.services.youth_access import require_youth_assigned_to_professional
from app.services.youth_queries import disable_youth_login
from app.services.youth_rut import normalize_rut


def update_youth_profile(
    db: DBSession,
    youth_id: int,
    prof: Professional,
    data: YouthUpdate,
) -> tuple[Youth, str | None]:
    """Actualiza campos del joven; invitación si login sin user_id. Commit y refresh. Devuelve activation_url opcional."""
    youth = require_youth_assigned_to_professional(db, youth_id, prof)
    prev_login_enabled = youth.login_enabled
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("identifier", None)
    email = update_data.pop("email", None)
    profile_checklist = update_data.pop("profile_checklist", None)
    if "rut" in update_data:
        raw_rut = update_data.get("rut")
        if raw_rut:
            normalized_rut = normalize_rut(raw_rut)
            existing_rut = db.query(Youth).filter(Youth.rut == normalized_rut, Youth.id != youth_id).first()
            if existing_rut:
                raise HTTPException(status_code=409, detail="El RUT ya está registrado")
            update_data["rut"] = normalized_rut
        else:
            update_data["rut"] = None
    for k, v in update_data.items():
        setattr(youth, k, v)
    if profile_checklist is not None:
        youth.profile_checklist = json.dumps(profile_checklist) if profile_checklist else None
    if "login_enabled" in update_data and update_data["login_enabled"] is False and prev_login_enabled:
        disable_youth_login(db, youth)
    activation_url = None
    if youth.login_enabled and not youth.user_id and email:
        email = email.lower().strip()
        if not email:
            raise HTTPException(status_code=400, detail="Correo inválido")
        existing = db.query(User).filter(User.email.ilike(email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="El correo ya está registrado")
        token = str(uuid.uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=email, token=token, expires_at=expires))
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    db.refresh(youth)
    return youth, activation_url


def change_youth_email_for_professional(
    db: DBSession,
    youth_id: int,
    prof: Professional,
    data: YouthChangeEmailRequest,
) -> tuple[Youth, str]:
    """Invalida invitaciones pendientes, crea nueva invitación con el correo indicado. Commit y refresh."""
    youth = require_youth_assigned_to_professional(db, youth_id, prof)
    if not youth.login_enabled:
        raise HTTPException(status_code=400, detail="El joven no tiene login habilitado")
    new_email = data.new_email.lower().strip()
    if not new_email:
        raise HTTPException(status_code=400, detail="Correo inválido")
    existing = db.query(User).filter(User.email.ilike(new_email)).first()
    if existing and (not youth.user_id or existing.id != youth.user_id):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    now = datetime.now(timezone.utc)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )
    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    db.add(YouthInvitation(youth_id=youth.id, email=new_email, token=token, expires_at=expires))
    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    db.refresh(youth)
    return youth, activation_url


def deactivate_youth_for_professional(
    db: DBSession,
    youth_id: int,
    prof: Professional,
) -> Youth:
    """Marca joven inactivo. Commit y refresh."""
    youth = require_youth_assigned_to_professional(db, youth_id, prof)
    youth.is_active = False
    db.commit()
    db.refresh(youth)
    return youth


def activate_youth_for_professional(
    db: DBSession,
    youth_id: int,
    prof: Professional,
) -> Youth:
    """Marca joven activo. Commit y refresh."""
    youth = require_youth_assigned_to_professional(db, youth_id, prof)
    youth.is_active = True
    db.commit()
    db.refresh(youth)
    return youth
