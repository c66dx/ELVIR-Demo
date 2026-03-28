"""Generación de identificadores JOV-NNN y creación de jóvenes con reintentos ante colisiones."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.models.youth import Youth

MAX_IDENTIFIER_RETRIES = 3


def generate_identifier(db: DBSession) -> str:
    """Genera el siguiente identificador (JOV-001, JOV-002, ...)."""
    candidates = db.query(Youth.identifier).filter(Youth.identifier.like("JOV-%")).all()
    max_num = 0
    for (raw_ident,) in candidates:
        if not raw_ident:
            continue
        ident = raw_ident.strip()
        try:
            n = int(ident[4:])
            if n > max_num:
                max_num = n
        except (ValueError, IndexError):
            continue
    return f"JOV-{max_num + 1:03d}"


def create_youth_with_unique_identifier(
    db: DBSession,
    *,
    display_name: str,
    rut: str | None = None,
    phone: str | None,
    year_of_birth: int | None = None,
    diagnosis: str | None = None,
    login_enabled: bool,
    general_notes: str | None,
    profile_checklist_json: str | None,
) -> Youth:
    """Crea Youth con reintento acotado ante colisión de identificador concurrente."""
    for _ in range(MAX_IDENTIFIER_RETRIES):
        identifier = generate_identifier(db)
        try:
            with db.begin_nested():
                youth = Youth(
                    display_name=display_name,
                    identifier=identifier,
                    rut=rut,
                    phone=phone,
                    year_of_birth=year_of_birth,
                    diagnosis=diagnosis,
                    login_enabled=login_enabled,
                    general_notes=general_notes,
                    profile_checklist=profile_checklist_json,
                    photo_url=None,
                    is_active=True,
                )
                db.add(youth)
                db.flush()
                return youth
        except IntegrityError:
            continue

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No fue posible generar un identificador único para el joven. Reintenta.",
    )
