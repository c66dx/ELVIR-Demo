"""Creación de jóvenes por profesional (perfil + asignación + invitación opcional)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models.assignment import Assignment
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.schemas.youth import YouthCreate
from app.services.youth_identifiers import create_youth_with_unique_identifier
from app.services.youth_rut import normalize_rut


def create_youth_for_professional(
    db: DBSession,
    data: YouthCreate,
    prof: Professional,
) -> tuple[Youth, str | None]:
    """Valida email/RUT, crea joven, asignación ACTIVO e invitación si aplica. Hace commit."""
    profile_checklist_json = json.dumps(data.profile_checklist) if data.profile_checklist else None
    email = None
    if data.login_enabled and data.email:
        email = data.email.lower().strip()
        if not email:
            raise HTTPException(status_code=400, detail="Correo inválido")
        existing = db.query(User).filter(User.email.ilike(email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="El correo ya está registrado")
    normalized_rut = None
    if data.rut:
        normalized_rut = normalize_rut(data.rut)
        existing_rut = db.query(Youth).filter(Youth.rut == normalized_rut).first()
        if existing_rut:
            raise HTTPException(status_code=409, detail="El RUT ya está registrado")
    youth = create_youth_with_unique_identifier(
        db,
        display_name=data.display_name,
        rut=normalized_rut,
        phone=data.phone,
        year_of_birth=data.year_of_birth,
        diagnosis=data.diagnosis,
        login_enabled=data.login_enabled,
        general_notes=data.general_notes,
        profile_checklist_json=profile_checklist_json,
    )
    db.add(Assignment(youth_id=youth.id, professional_id=prof.id, status="ACTIVO"))
    db.flush()
    activation_url = None
    if data.login_enabled and email:
        token = str(uuid.uuid4())
        expires = datetime.now(UTC) + timedelta(days=7)
        db.add(YouthInvitation(youth_id=youth.id, email=email, token=token, expires_at=expires))
        activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    return youth, activation_url
