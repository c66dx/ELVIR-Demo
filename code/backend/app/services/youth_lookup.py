"""Lookup de jóvenes por ID con filtrado por rol."""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.models.assignment import Assignment
from app.models.user import User
from app.models.youth import Youth
from app.services.youth_queries import get_user_profile_photo_map


def parse_lookup_ids(raw_ids: list) -> list[int]:
    """Normaliza lista de ids (int o string numérico) a enteros positivos únicos."""
    parsed = list({int(i) for i in raw_ids if isinstance(i, int) or (isinstance(i, str) and str(i).isdigit())})
    return [i for i in parsed if i > 0]


def lookup_youth_profiles(db: DBSession, user: User, ids: list[int]) -> list[dict]:
    """Devuelve id, display_name, rut, profile_photo_url respetando permisos de rol."""
    if not ids:
        return []

    q = db.query(Youth.id, Youth.display_name, Youth.rut, Youth.user_id, Youth.photo_url).filter(Youth.id.in_(ids))
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth or youth.id not in ids:
            return []
        q = q.filter(Youth.id == youth.id)
    elif user.role == "PROFESIONAL":
        from app.models.professional import Professional

        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            return []
        q = q.join(Assignment, Assignment.youth_id == Youth.id).filter(
            Assignment.professional_id == prof.id,
            Assignment.status == "ACTIVO",
        )
    elif user.role != "ADMIN":
        return []

    rows = q.all()
    user_ids = [r[3] for r in rows if r[3]]
    photo_map = get_user_profile_photo_map(db, user_ids)
    return [
        {
            "id": r[0],
            "display_name": r[1],
            "rut": r[2],
            "profile_photo_url": r[4] or photo_map.get(r[3]),
        }
        for r in rows
    ]
