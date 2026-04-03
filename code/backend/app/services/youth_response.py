"""Mapeo Youth ORM → esquemas de API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.youth import Youth
from app.schemas.youth import YouthResponse, parse_profile_checklist
from app.services.youth_queries import (
    get_pending_invitation_email,
    get_user_profile_photo,
    get_youth_email,
)


def youth_to_response(
    youth: Youth,
    activation_url: str | None = None,
    email: str | None = None,
    profile_photo_url: str | None = None,
) -> YouthResponse:
    """Convierte modelo Youth a YouthResponse. email viene del User cuando youth.user_id existe."""
    final_photo_url = youth.photo_url or profile_photo_url
    return YouthResponse(
        id=youth.id,
        user_id=youth.user_id,
        display_name=youth.display_name,
        identifier=youth.identifier,
        rut=youth.rut,
        email=email,
        profile_photo_url=final_photo_url,
        phone=youth.phone,
        year_of_birth=youth.year_of_birth,
        diagnosis=youth.diagnosis,
        login_enabled=youth.login_enabled,
        is_active=youth.is_active,
        general_notes=youth.general_notes,
        profile_checklist=parse_profile_checklist(youth.profile_checklist) or None,
        activation_url=activation_url,
    )


def youth_to_response_with_contact(
    db: Session,
    youth: Youth,
    *,
    activation_url: str | None = None,
    include_pending_invitation_email: bool = False,
) -> YouthResponse:
    """Resuelve email y foto desde User; opcionalmente muestra email de invitación pendiente si no hay user."""
    if youth.user_id:
        email = get_youth_email(db, youth.user_id)
    elif include_pending_invitation_email:
        email = get_pending_invitation_email(db, youth.id)
    else:
        email = None
    profile_photo_url = get_user_profile_photo(db, youth.user_id) if youth.user_id else None
    return youth_to_response(
        youth,
        activation_url=activation_url,
        email=email,
        profile_photo_url=profile_photo_url,
    )
